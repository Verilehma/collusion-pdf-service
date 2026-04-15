/**
 * pdf-generator.ts
 * Calls generate-pdf.py via Python subprocess and returns the PDF as a Buffer.
 * Place generate-pdf.py at the project root.
 */

import { execFile } from 'child_process'
import { promisify } from 'util'
import { readFile, unlink, mkdtemp } from 'fs/promises'
import { tmpdir } from 'os'
import path from 'path'

const execFileAsync = promisify(execFile)

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

const SCRIPT_PATH = path.resolve(process.cwd(), '..', '..', 'generate-pdf.py')
const PYTHON = process.platform === 'win32' ? 'python' : 'python3'

export async function generatePdfs(
  order: PdfOrder,
  types: ('invoice' | 'manifest')[] = ['invoice', 'manifest']
): Promise<GeneratedPdfs> {
  // Write order data to a temp JSON file so Python can read it
  const tmpDir = await mkdtemp(path.join(tmpdir(), 'collusion-pdf-'))
  const jsonPath = path.join(tmpDir, 'order.json')
  const { writeFile } = await import('fs/promises')
  await writeFile(jsonPath, JSON.stringify(order))

  const result: GeneratedPdfs = {}

  for (const type of types) {
    const outPath = path.join(tmpDir, `${order.id.replace(/\//g, '-')}-${type}.pdf`)

    try {
      await execFileAsync(PYTHON, [
        SCRIPT_PATH,
        type,
        '--json', jsonPath,
        '--out-dir', tmpDir,
      ], { timeout: 30_000 })

      result[type] = await readFile(outPath)
    } finally {
      // Clean up individual pdf (ignore errors)
      unlink(outPath).catch(() => {})
    }
  }

  // Clean up temp dir
  unlink(jsonPath).catch(() => {})

  return result
}
