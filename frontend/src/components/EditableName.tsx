import { useState } from 'react'

type Props = {
  value: string
  // Names the row, e.g. `group “Housing”`, so the accessible name says which
  // one this is.
  label: string
  onSave: (name: string) => void
}

// A name that becomes an input when clicked. Enter and clicking away save,
// Escape cancels. Used by both group rows and category rows.
export default function EditableName({ value, label, onSave }: Props) {
  // null means "not being edited".
  const [draft, setDraft] = useState<string | null>(null)

  function save() {
    const name = (draft ?? '').trim()
    setDraft(null)
    if (name !== '' && name !== value) {
      onSave(name)
    }
  }

  if (draft === null) {
    return (
      <button
        type="button"
        onClick={() => setDraft(value)}
        title={`Rename ${label}`}
        className="rounded px-1 text-left hover:bg-gray-100"
      >
        {value}
      </button>
    )
  }

  return (
    <input
      autoFocus
      value={draft}
      aria-label={`Rename ${label}`}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={save}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          save()
        }
        if (event.key === 'Escape') {
          setDraft(null)
        }
      }}
      className="w-56 rounded border border-gray-300 px-1 text-sm"
    />
  )
}
