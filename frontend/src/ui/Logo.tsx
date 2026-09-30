import { Link } from "react-router";

export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2 font-semibold tracking-tight" aria-label="IT Match — на главную">
      <span aria-hidden className="grid size-7 place-items-center rounded-lg bg-accent text-sm font-bold text-on-accent">
        IT
      </span>
      <span>
        IT Match <span className="text-muted">· ФСП</span>
      </span>
    </Link>
  );
}
