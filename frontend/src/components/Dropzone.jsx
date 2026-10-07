// Drag-and-drop file picker with client-side type/size checks (the server re-validates).
import { useDropzone } from 'react-dropzone'
import Icon from './Icon.jsx'

const MAX_BYTES = 5 * 1024 * 1024
const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}
const REJECTION_TEXT = {
  'file-invalid-type': 'Only PDF and DOCX files are supported.',
  'file-too-large': 'The file is larger than 5 MB.',
  'too-many-files': 'Please upload one file at a time.',
}

export default function Dropzone({ file, onFile, onReject, disabled }) {
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPT, maxSize: MAX_BYTES, multiple: false, disabled, noClick: Boolean(file),
    onDropAccepted: (files) => onFile(files[0]),
    onDropRejected: (rejections) => onReject(REJECTION_TEXT[rejections[0]?.errors[0]?.code] || 'That file cannot be used.'),
  })

  return (
    <div>
      <p id="dropzone-label" className="eyebrow mb-4">02 · Resume</p>
      <div {...getRootProps({ 'aria-labelledby': 'dropzone-label', 'aria-describedby': 'dropzone-hint' })}
        className={`focus-ring relative flex min-h-48 flex-col items-center justify-center rounded-3xl border border-dashed px-6 py-10 text-center transition-all duration-300
          ${isDragActive ? 'border-ink bg-surface' : 'border-line-strong bg-surface/40 hover:bg-surface/80'}
          ${file ? '' : 'cursor-pointer'} ${disabled ? 'pointer-events-none opacity-60' : ''}`}>
        <input {...getInputProps()} />
        {file ? (
          <div className="flex w-full max-w-md items-center gap-4 rounded-2xl border border-line bg-surface p-4 text-left">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface-2 text-ink-2">
              <Icon name="file" className="size-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink">{file.name}</span>
              <span className="block text-xs text-ink-3">{(file.size / 1024).toFixed(0)} KB · ready</span>
            </span>
            <button type="button" onClick={open} className="btn-ghost !h-8 !px-3 text-xs">Replace</button>
          </div>
        ) : (
          <>
            <span className={`grid size-11 place-items-center rounded-full border transition-all duration-300
              ${isDragActive ? 'scale-110 border-ink bg-ink text-page' : 'border-line-strong text-ink-2'}`}>
              <Icon name="upload" className="size-5" />
            </span>
            <p className="mt-4 text-[15px] text-ink">{isDragActive ? 'Release to upload' : 'Drop your resume here'}</p>
            <p id="dropzone-hint" className="mt-1 text-sm text-ink-3">
              or <span className="text-ink underline decoration-line-strong underline-offset-4">browse files</span> · PDF or DOCX, up to 5 MB
            </p>
          </>
        )}
      </div>
    </div>
  )
}
