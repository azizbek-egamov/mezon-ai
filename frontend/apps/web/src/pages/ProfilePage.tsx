/** Profil: F.I.Sh., advokatlik guvohnomasi, interfeys tili; chiqish. */
import { ApiError } from "@mezon/api-client";
import { LogOutIcon, SaveIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button, Card, FieldError, formatDate, Input, Label, LanguageSelect, PageHeader, Spinner, ThemeSwitch, useAuth, useLanguage } from "@mezon/web-kit";

import { Avatar } from "@/components/layout/AppShell";

export function ProfilePage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { user, updateMe, logout } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [license, setLicense] = useState(user?.advocate_license_no ?? "");
  const [university, setUniversity] = useState(user?.university ?? "");
  const [studyLevel, setStudyLevel] = useState(user?.study_level ?? "");
  const [studentIdNo, setStudentIdNo] = useState(user?.student_id_no ?? "");
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);
  if (!user) return null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await updateMe({
        full_name: fullName,
        advocate_license_no: license,
        university,
        study_level: studyLevel,
        student_id_no: studentIdNo,
      });
      setErrors({});
      toast.success(t("Saqlandi"));
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6 px-5 py-10 sm:px-8">
      <PageHeader title={t("Profil")} className="mb-2" />
      <Card className="animate-in-up p-7">
        <div className="flex items-center gap-4">
          <Avatar name={user.full_name} className="size-12 text-base" />
          <div className="min-w-0">
            <div className="truncate font-serif text-lg font-semibold">{user.full_name}</div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-muted">
              <span className="tabular-nums">{user.phone_number}</span>
              <span>{user.role_label}</span>
              <span>{formatDate(user.date_joined, language)}</span>
            </div>
          </div>
        </div>
        <form onSubmit={submit} className="mt-7 flex flex-col gap-5 border-t border-line pt-7">
          <div>
            <Label htmlFor="full_name">{t("F.I.Sh.")}</Label>
            <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} aria-invalid={!!errors.full_name} />
            <FieldError messages={errors.full_name} />
          </div>
          {user.role === "LAWYER" && (
            <div>
              <Label htmlFor="license">{t("Advokatlik guvohnomasi raqami")}</Label>
              <Input id="license" className="tabular-nums" value={license} onChange={(e) => setLicense(e.target.value)} />
              <FieldError messages={errors.advocate_license_no} />
            </div>
          )}
          {user.role === "STUDENT" && (
            <div className="flex flex-col gap-4">
              <div>
                <Label htmlFor="university">{t("Universitet / OTM")}</Label>
                <Input
                  id="university"
                  value={university}
                  onChange={(e) => setUniversity(e.target.value)}
                  placeholder={t("Masalan: TDYU, SamDU, OʻzMU...")}
                  aria-invalid={!!errors.university}
                />
                <FieldError messages={errors.university} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="study_level">{t("Bosqich / Kurs")}</Label>
                  <Input
                    id="study_level"
                    value={studyLevel}
                    onChange={(e) => setStudyLevel(e.target.value)}
                    placeholder={t("Masalan: 3-kurs, Magistratura...")}
                    aria-invalid={!!errors.study_level}
                  />
                  <FieldError messages={errors.study_level} />
                </div>
                <div>
                  <Label htmlFor="student_id">{t("Talaba guvohnomasi / ID")}</Label>
                  <Input
                    id="student_id"
                    value={studentIdNo}
                    onChange={(e) => setStudentIdNo(e.target.value)}
                    placeholder={t("Masalan: TDYU-12345")}
                    aria-invalid={!!errors.student_id_no}
                  />
                  <FieldError messages={errors.student_id_no} />
                </div>
              </div>
            </div>
          )}
          <div>
            <Label>{t("Interfeys tili")}</Label>
            <LanguageSelect className="h-10 w-full text-sm" />
          </div>
          <div>
            <Label>{t("Koʻrinish")}</Label>
            <ThemeSwitch />
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button type="submit" disabled={busy}>{busy ? <Spinner className="text-primary-foreground" /> : <SaveIcon />}{t("Saqlash")}</Button>
            <Button type="button" variant="destructive" onClick={() => void logout()}><LogOutIcon />{t("Chiqish")}</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
