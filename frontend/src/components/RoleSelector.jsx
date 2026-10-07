// Radio group for choosing the target role.
import Icon from './Icon.jsx'

export default function RoleSelector({ roles, value, onChange, disabled }) {
  return (
    <fieldset disabled={disabled}>
      <legend className="eyebrow mb-4">01 · Target role</legend>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((role) => {
          const checked = value === role.id
          return (
            <label key={role.id}
              className={`group relative flex cursor-pointer flex-col rounded-2xl border px-4 py-3.5 transition-all duration-200
                has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent/70
                ${checked ? 'border-ink bg-surface' : 'border-line bg-surface/50 hover:border-line-strong hover:bg-surface'}`}>
              <input type="radio" name="role" value={role.id} checked={checked} onChange={() => onChange(role.id)} className="sr-only" />
              <span className="flex items-center justify-between gap-2">
                <span className="text-[15px] font-medium text-ink">{role.name}</span>
                <span aria-hidden="true"
                  className={`grid size-4 place-items-center rounded-full transition-all ${checked ? 'bg-ink text-page' : 'border border-line-strong'}`}>
                  {checked && <Icon name="check" className="size-2.5" />}
                </span>
              </span>
              <span className="mt-1 truncate text-xs text-ink-3">
                {role.must_have.slice(0, 3).map((m) => m.label).join(' · ')}
              </span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
