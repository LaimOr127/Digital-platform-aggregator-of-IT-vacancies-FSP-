import { useEffect, useState } from "react";

/** Значение, обновляемое не чаще раза в delay мс — для поиска без запроса на каждую букву. */
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
