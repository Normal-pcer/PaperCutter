import axios from 'axios'
import type { PdfInfo, AutoCutResult, PasteItem, OutputPage } from '../types'

const api = axios.create({
  baseURL: 'http://127.0.0.1:7652/api',
  timeout: 120000,
})

// ─── PDF Upload ───────────────────────────────────────────────────────

export async function uploadPdf(file: File): Promise<PdfInfo> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<PdfInfo>('/pdf/upload', form)
  return data
}

// ─── Auto-Cut ─────────────────────────────────────────────────────────

export async function autoCut(
  fileId: string,
  strategy: 'content' | 'image' = 'content',
  params?: Record<string, number>
): Promise<AutoCutResult> {
  const { data } = await api.post<AutoCutResult>(`/auto-cut/${fileId}`, {
    strategy,
    ...params,
  })
  return data
}

// ─── Build Output PDF ─────────────────────────────────────────────────

export async function buildPdf(
  fileId: string,
  pastes: PasteItem[],
  pages: OutputPage[]
): Promise<Blob> {
  const { data } = await api.post(
    '/build',
    { fileId, pastes, pages },
    { responseType: 'blob' }
  )
  return data as Blob
}

// ─── PDF Info ─────────────────────────────────────────────────────────

export async function getPdfInfo(fileId: string): Promise<PdfInfo> {
  const { data } = await api.get<PdfInfo>(`/pdf/${fileId}/info`)
  return data
}

// ─── Page Image (fallback) ────────────────────────────────────────────

export function getPageImageUrl(fileId: string, pageNum: number, dpi = 150): string {
  return `http://127.0.0.1:7652/api/pdf/${fileId}/page/${pageNum}/image?dpi=${dpi}`
}
