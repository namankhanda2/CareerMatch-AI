export default function SkillPills({ items, variant = "match" }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-500">None identified.</p>;
  }

  const styles =
    variant === "missing"
      ? "border-rose-100 bg-rose-50 text-rose-800"
      : "border-emerald-100 bg-emerald-50 text-emerald-800";

  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((skill, index) => (
        <li
          key={`${index}-${skill}`}
          className={`rounded-full border px-3 py-1 text-sm font-medium ${styles}`}
        >
          {skill}
        </li>
      ))}
    </ul>
  );
}
