// Radio-card group for choosing the target role.
export default function RoleSelector({ roles, value, onChange, disabled }) {
  return (
    <fieldset disabled={disabled}>
      <legend className="mb-3 text-sm font-semibold text-ink">1. Choose your target role</legend>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((role) => {
          const checked = value === role.id
          return (
            <label key={role.id}
              className={`group relative flex cursor-pointer flex-col rounded-xl border p-3.5 transition
                has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent
                ${checked ? 'border-accent bg-accent/10' : 'border-line bg-card hover:-translate-y-0.5 hover:border-ink-3'}`}>
              <input type="radio" name="role" value={role.id} checked={checked} onChange={() => onChange(role.id)} className="sr-only" />
              <span className="flex items-center justify-between gap-2">
                <span className="font-medium text-ink">{role.name}</span>
                <span aria-hidden="true" className={`size-4 rounded-full border-2 transition ${checked ? 'border-accent bg-accent ring-2 ring-inset ring-card' : 'border-ink-3'}`} />
              </span>
              <span className="mt-1 line-clamp-2 text-xs text-ink-3">
                {role.must_have.slice(0, 4).map((m) => m.label).join(' · ')}
              </span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
