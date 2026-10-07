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
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPT, maxSize: MAX_BYTES, multiple: false, disabled,
    onDropAccepted: (files) => onFile(files[0]),
    onDropRejected: (rejections) => onReject(REJECTION_TEXT[rejections[0]?.errors[0]?.code] || 'That file cannot be used.'),
  })

  return (
    <div>
      <p id="dropzone-label" className="mb-3 text-sm font-semibold text-ink">2. Upload your resume</p>
      <div {...getRootProps({ 'aria-labelledby': 'dropzone-label', 'aria-describedby': 'dropzone-hint' })}
        className={`focus-ring flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition
          ${isDragActive ? 'scale-[1.01] border-accent bg-accent/10' : 'border-line bg-card hover:border-ink-3'}
          ${disabled ? 'pointer-events-none opacity-60' : ''}`}>
        <input {...getInputProps()} />
        <span className={`grid size-12 place-items-center rounded-full transition ${isDragActive ? 'bg-accent text-white' : 'bg-card-2 text-ink-2'}`}>
          <Icon name={file ? 'file' : 'upload'} className="size-6" />
        </span>
        {file ? (
          <div>
            <p className="font-medium text-ink break-all">{file.name}</p>
            <p className="text-sm text-ink-3">{(file.size / 1024).toFixed(0)} KB · click or drop to replace</p>
          </div>
        ) : (
          <div>
            <p className="font-medium text-ink">{isDragActive ? 'Drop it here' : 'Drag and drop your resume, or click to browse'}</p>
            <p id="dropzone-hint" className="text-sm text-ink-3">PDF or DOCX, up to 5 MB</p>
          </div>
        )}
      </div>
    </div>
  )
}
