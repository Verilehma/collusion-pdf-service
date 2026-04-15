/**
 * pdf-generator.ts
 * Calls the Railway PDF microservice and returns PDFs as Buffers.
 * Set PDF_SERVICE_URL and PDF_SERVICE_SECRET in .env.local
 */

// ── Types ──────────────────────────────────────────────────────────────────────

export interface PdfOrderAgent {
  name: string
  business_id: string
  address: string
  email: string
  phone: string
  iban: string
  bic: string
}

export interface PdfOrderCustomer {
  name: string
  business_id: string
  address: string
  contact: string
  email: string
  phone: string
}

export interface PdfOrderDelivery {
  address: string
  date: string
  driver?: string
  vehicle?: string
}

export interface PdfOrderLine {
  sku: string
  name: string
  producer: string
  region: string
  vintage: number
  bottle_size: string
  cases: number
  bottles_per_case: number
  unit_price: number
  vat_pct: number
}

export interface PdfOrder {
  id: string
  created_at: string
  due_date: string
  status: string
  notes?: string
  agent: PdfOrderAgent
  customer: PdfOrderCustomer
  delivery: PdfOrderDelivery
  lines: PdfOrderLine[]
}

export interface GeneratedPdfs {
  invoice?: Buffer
  manifest?: Buffer
}

// ── Generator ──────────────────────────────────────────────────────────────────

const PDF_SERVICE_URL = process.env.PDF_SERVICE_URL?.replace(/\/$/, '') ?? ''
const PDF_SERVICE_SECRET = process.env.PDF_SERVICE_SECRET ?? ''

function getHeaders() {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (PDF_SERVICE_SECRET) headers['Authorization'] = `Bearer ${PDF_SERVICE_SECRET}`
  return headers
}

async function fetchPdf(endpoint: string, order: PdfOrder): Promise<Buffer> {
  const url = `${PDF_SERVICE_URL}${endpoint}`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(order),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`PDF service error ${res.status}: ${text}`)
  }
  const arrayBuffer = await res.arrayBuffer()
  return Buffer.from(arrayBuffer)
}

export async function generatePdfs(
  order: PdfOrder,
  types: ('invoice' | 'manifest')[] = ['invoice', 'manifest']
): Promise<GeneratedPdfs> {
  if (!PDF_SERVICE_URL) {
    throw new Error('PDF_SERVICE_URL environment variable is not set')
  }

  const result: GeneratedPdfs = {}

  // Fetch both in parallel if both requested
  const tasks: Promise<void>[] = []

  if (types.includes('invoice')) {
    tasks.push(
      fetchPdf('/generate/invoice', order).then(buf => { result.invoice = buf })
    )
  }

  if (types.includes('manifest')) {
    tasks.push(
      fetchPdf('/generate/manifest', order).then(buf => { result.manifest = buf })
    )
  }

  await Promise.all(tasks)
  return result
}
