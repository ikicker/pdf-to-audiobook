/**
 * PathInput.tsx
 * Mirrors Python's PathSelectionWidget: a read-only display + Browse button.
 */

interface Props {
  value: string
  placeholder?: string
  mode: 'file-open-pdf' | 'file-save-audio' | 'directory'
  onChange: (path: string) => void
}

export default function PathInput({ value, placeholder = 'Browse…', mode, onChange }: Props) {
  const browse = async () => {
    if (mode === 'file-open-pdf') {
      const result = await window.electron.dialogOpenFile('pdf')
      if (!result.canceled && result.filePaths[0]) onChange(result.filePaths[0])
    } else if (mode === 'file-save-audio') {
      const result = await window.electron.dialogSaveFile('audio')
      if (!result.canceled && result.filePath) onChange(result.filePath)
    } else {
      const result = await window.electron.dialogOpenDir()
      if (!result.canceled && result.filePaths[0]) onChange(result.filePaths[0])
    }
  }

  const display = value
    ? value.replace(/\\/g, '/').split('/').slice(-2).join('/')
    : ''

  return (
    <div className="path-input">
      <span
        className={`path-input__text ${!value ? 'path-input__text--empty' : ''}`}
        title={value || placeholder}
      >
        {display || placeholder}
      </span>
      <button className="btn btn--browse" onClick={browse}>…</button>
    </div>
  )
}
