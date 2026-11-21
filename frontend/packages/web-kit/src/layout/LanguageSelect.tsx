import { LANGUAGES, type LanguageCode } from "@mezon/i18n";

import { useLanguage } from "../lib/i18n";
import { cn } from "../lib/utils";
import { CustomSelect } from "../ui/select";

/** Interfeys tili tanlagichi: har bir til o'z yozuvida (Oʻzbekcha, Ўзбекча, Русский, Қарақалпақша, English). */
export function LanguageSelect({ className }: { className?: string }) {
  const { language, setLanguage } = useLanguage();
  return (
    <CustomSelect
      value={language}
      onValueChange={(val) => setLanguage(val as LanguageCode)}
      aria-label="Til / Язык / Language"
      title="Til / Язык / Language"
      size="sm"
      className={cn("w-auto min-w-[136px]", className)}
      options={LANGUAGES.map((l) => ({ value: l.code, label: l.name }))}
    />
  );
}
