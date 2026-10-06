// QR-код ссылки: генерируется в браузере в data:URL (CSP разрешает img-src data:).
import QRCode from "qrcode";
import { useEffect, useState } from "react";

export function QrCode({ value, size = 160, label }: { value: string; size?: number; label: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    QRCode.toDataURL(value, { margin: 1, width: size * 2, errorCorrectionLevel: "M" })
      .then((url) => active && setSrc(url))
      .catch(() => active && setSrc(null));
    return () => {
      active = false;
    };
  }, [value, size]);
  return (
    <div className="inline-block rounded-xl bg-white p-2" style={{ width: size + 16, height: size + 16 }}>
      {src && <img src={src} width={size} height={size} alt={label} />}
    </div>
  );
}
