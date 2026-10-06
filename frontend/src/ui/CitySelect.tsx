// Город из справочника: фильтр работодателя и подбор сравнивают одинаковые названия.
import type { SelectHTMLAttributes } from "react";
import { useDictionaries } from "../api/queries";
import { Select } from "./form";

// value — unknown: поля форм проходят через zod.preprocess, тип ввода у них не сужен
type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "value"> & { value: unknown; placeholder?: string };

export function CitySelect({ value: raw, placeholder = "Не выбран", ...rest }: Props) {
  const value = typeof raw === "string" ? raw : "";
  const cities = useDictionaries().data?.cities ?? [];
  // значение, которого нет в справочнике (старые данные), остаётся видимым, чтобы его заменить
  const list = value && !cities.includes(value) ? [value, ...cities] : cities;
  return (
    <Select
      placeholder={placeholder}
      options={list.map((city) => ({ value: city, label: city }))}
      value={value}
      {...rest}
    />
  );
}
