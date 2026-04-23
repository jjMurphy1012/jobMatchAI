import { useCallback, useEffect, useState } from 'react'
import { CheckCircle, ExternalLink, FileText, Trash2, Upload, Wand2 } from 'lucide-react'

import { ResumeResponse, resumeApi } from '../api/client'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export default function Resume() {
  const [resume, setResume] = useState<ResumeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadResume()
  }, [])

  async function loadResume() {
    setLoading(true)
    const result = await resumeApi.get()
    if (result.data) {
      setResume(result.data)
    }
    setLoading(false)
  }

  const handleDrag = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (event.type === 'dragenter' || event.type === 'dragover') {
      setDragActive(true)
    } else if (event.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(false)

    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      handleFile(event.dataTransfer.files[0])
    }
  }, [])

  const handleFileInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      handleFile(event.target.files[0])
    }
  }

  async function handleFile(file: File) {
    if (!file.name.endsWith('.pdf')) {
      setError('Please upload a PDF file')
      return
    }

    setUploading(true)
    setError(null)

    const result = await resumeApi.upload(file)

    if (result.error) {
      setError(result.error)
    } else if (result.data) {
      setResume(result.data)
    }

    setUploading(false)
  }

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete your resume?')) return

    const result = await resumeApi.delete()
    if (!result.error) {
      setResume(null)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_38%),radial-gradient(circle_at_right,_rgba(14,159,110,0.08),_transparent_26%)]" />
        <div className="relative grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/10 bg-primary/5 px-3 py-1 text-sm font-semibold text-primary">
              <Wand2 className="h-4 w-4" />
              Resume Setup
            </div>
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                Upload the resume you want every future match to use.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600">
                A fresh PDF here improves ranking quality, cover letter quality, and interview prep relevance.
                Replace it any time before you run Match again.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-[1.5rem] border border-white/80 bg-white/88 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Format</p>
                <p className="mt-3 text-xl font-semibold text-slate-900">PDF only</p>
              </div>
              <div className="rounded-[1.5rem] border border-white/80 bg-white/88 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Storage</p>
                <p className="mt-3 text-xl font-semibold text-slate-900">{resume?.storage_provider || 'Supabase'}</p>
              </div>
              <div className="rounded-[1.5rem] border border-white/80 bg-white/88 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Status</p>
                <p className="mt-3 text-xl font-semibold text-slate-900">{resume ? 'Ready' : 'Waiting'}</p>
              </div>
            </div>
          </div>

          <div className="rounded-[1.85rem] border border-white/80 bg-white/88 p-5 shadow-[0_24px_55px_-35px_rgba(55,65,81,0.3)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Current file</p>
            {resume ? (
              <div className="mt-5 space-y-4">
                <div className="flex items-start gap-4 rounded-[1.5rem] border border-emerald-100 bg-emerald-50/70 p-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100">
                    <CheckCircle className="h-6 w-6 text-emerald-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-base font-semibold text-slate-900">{resume.file_name}</p>
                    <p className="mt-1 text-sm text-slate-500">
                      Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                {resume.content_preview && (
                  <div className="rounded-[1.35rem] border border-slate-200 bg-slate-50/90 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Preview</p>
                    <p className="mt-3 text-sm leading-6 text-slate-600 line-clamp-6">{resume.content_preview}...</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-3">
                  {resume.download_url && (
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => window.open(resume.download_url, '_blank')}
                    >
                      Open file
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  )}
                  <Button variant="outline" className="gap-2 text-red-600 hover:text-red-700" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/80 p-6 text-center text-sm leading-6 text-slate-500">
                No resume uploaded yet. Drop a PDF below to start the matching flow.
              </div>
            )}
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-[1.35rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-xl font-semibold">Drop in a new PDF</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className={`rounded-[1.75rem] border-2 border-dashed p-8 text-center transition-all sm:p-10 ${
              dragActive
                ? 'border-primary bg-primary/5'
                : 'border-slate-300 bg-slate-50/70 hover:border-primary/40 hover:bg-white'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileInput}
              className="hidden"
              id="resume-upload"
              disabled={uploading}
            />

            <label htmlFor="resume-upload" className="flex cursor-pointer flex-col items-center">
              {uploading ? (
                <div className="mb-5 h-12 w-12 animate-spin rounded-full border-b-2 border-primary" />
              ) : (
                <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-primary/10 text-primary">
                  <Upload className="h-7 w-7" />
                </div>
              )}

              <p className="text-lg font-semibold text-slate-900">
                {uploading ? 'Uploading your resume...' : 'Drop your PDF resume here'}
              </p>
              <p className="mt-2 text-sm text-slate-500">or click to browse from your device</p>
            </label>
          </div>

          <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
            <FileText className="h-4 w-4" />
            Only PDF files are supported. Your resume is used for matching and interview prep.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
