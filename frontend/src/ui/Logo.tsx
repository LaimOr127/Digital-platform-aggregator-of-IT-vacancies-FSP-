import { Link } from "react-router";
import star from "../assets/fsp-star.svg";
import starLight from "../assets/fsp-star-light.svg";

/** Знак ФСП (брендбук) и название сервиса — «IT» только в названии. На экране — вариант для
 * тёмного фона, при печати PDF-профиля — для светлого (белые элементы знака не пропадают). */
export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="IT Match · ФСП — на главную">
      <img src={star} alt="" aria-hidden className="size-8 print:hidden" />
      <img src={starLight} alt="" aria-hidden className="hidden size-8 print:block" />
      <span className="font-accent text-lg leading-none tracking-wide">IT Match</span>
      <span className="font-display text-sm text-muted">· ФСП</span>
    </Link>
  );
}
