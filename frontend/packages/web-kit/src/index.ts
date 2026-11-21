/**
 * @mezon/web-kit — veb-sayt (apps/web) va admin panel (apps/admin) uchun umumiy poydevor:
 * shadcn uslubidagi UI komponentlari (DESIGN.md tokenlari, `theme.css`), API klient (HttpOnly refresh cookie),
 * auth va til provayderlari, yordamchilar.
 */
export { api, postJson, restoreSession, setApiLanguage, tokenStore } from "./lib/api";
export { AuthProvider, useAuth, type RegisterData } from "./lib/auth";
export { fieldErrors, notifyError } from "./lib/errors";
export { LanguageProvider, useLanguage } from "./lib/i18n";
export { ThemeProvider, ThemeSwitch, useTheme, type ThemePref } from "./lib/theme";
export { cn, safeNext, formatDate, formatDateTime, formatMoney, saveBlob } from "./lib/utils";
export { extractUzPhoneDigits, formatUzPhoneDisplay, formatUzPhone } from "./lib/phone";
export { LanguageSelect } from "./layout/LanguageSelect";
export { Logo, LogoMark } from "./layout/Logo";
export { RouteError } from "./layout/RouteError";
export { Badge, CiteChip } from "./ui/badge";
export { Button } from "./ui/button";
export { Card, CardContent, CardHeader, CardTitle, PageHeader, SectionLabel } from "./ui/card";
export { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "./ui/dialog";
export { FieldError, Input, Label, NativeSelect, PasswordInput, PhoneInput, Textarea } from "./ui/input";
export { DatePicker, type DatePickerProps } from "./ui/date-picker";
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
  CustomSelect,
  SelectField,
  type SelectOption,
  type CustomSelectProps,
} from "./ui/select";
export { Checkbox, Empty, ErrorNote, Progress, Spinner, Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/misc";
export { FadeIn, PageTransition, Skeleton, staggerDelay, staggerStyle, TopLoader } from "./ui/motion";
