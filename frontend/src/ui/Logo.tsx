import { Link } from "react-router";
import star from "../assets/fsp-star.svg";

/** Знак ФСП (брендбук, вариант для тёмного фона) и название сервиса — «IT» только в названии. */
export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="IT Match · ФСП — на главную">
      <img src={star} alt="" aria-hidden className="size-8" />
      <span className="font-accent text-lg leading-none tracking-wide">IT Match</span>
      <span className="font-display text-sm text-muted">· ФСП</span>
    </Link>
  );
}
