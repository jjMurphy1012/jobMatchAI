import { useEffect, useState, useCallback } from 'react'
import { Upload, Trash2, CheckCircle } from 'lucide-react'
import { resumeApi, ResumeResponse } from '../api/client'

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

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Resume</h1>
      <p className="text-gray-600 mb-8">
        Upload your resume to get personalized job matches
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {resume ? (
        /* Resume Uploaded State */
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <CheckCircle className="text-green-600" size={24} />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">{resume.file_name}</h3>
              <p className="text-sm text-gray-500 mt-1">
                Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}
              </p>

              {resume.content_preview && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Preview</h4>
                  <p className="text-sm text-gray-600 line-clamp-4">
                    {resume.content_preview}...
                  </p>
                </div>
              )}
            </div>
            <button
              onClick={handleDelete}
              className="text-red-600 hover:text-red-700 p-2"
              title="Delete resume"
            >
              <Trash2 size={20} />
            </button>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Want to upload a new version? Just drop a new file below.
            </p>
          </div>
        </div>
      ) : null}

      {/* Upload Area */}
      <div
        className={`mt-6 border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          dragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
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

        <label
          htmlFor="resume-upload"
          className="cursor-pointer flex flex-col items-center"
        >
          {uploading ? (
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
          ) : (
            <div className="bg-gray-100 p-4 rounded-full mb-4">
              <Upload className="text-gray-600" size={24} />
            </div>
          )}

          <p className="text-gray-700 font-medium">
            {uploading ? 'Uploading...' : 'Drop your PDF resume here'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            or click to browse
          </p>
        </label>
      </div>

      <p className="text-xs text-gray-400 mt-4 text-center">
        Only PDF files are supported. Your resume will be processed by AI for job matching.
      </p>
    </div>
  )
}
