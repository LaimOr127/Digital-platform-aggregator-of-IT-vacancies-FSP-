// Водяной знак поверх заданий: идентификатор кандидата на снимке экрана показывает, чья это утечка.
const ROWS = 8;
const PER_ROW = 4;

export function Watermark({ text }: { text: string }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-10 select-none overflow-hidden">
      <div className="flex h-full -rotate-12 flex-col justify-around opacity-[0.07]">
        {Array.from({ length: ROWS }, (_, row) => (
          <p key={row} className="whitespace-nowrap text-lg font-semibold tracking-widest">
            {Array.from({ length: PER_ROW }, () => text).join("     ")}
          </p>
        ))}
      </div>
    </div>
  );
}
