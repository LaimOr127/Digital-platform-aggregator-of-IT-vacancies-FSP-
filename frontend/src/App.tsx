import { useEffect, useState } from "react";
import { apiGet } from "./api";

export function App() {
  const [status, setStatus] = useState<string>("проверка…");

  useEffect(() => {
    apiGet<{ status: string }>("/health")
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("недоступно"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 32 }}>
      <h1>IT Match · ФСП</h1>
      <p>Каркас платформы. API: {status}</p>
    </main>
  );
}
