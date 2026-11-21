/**
 * Huquqiy savol-javob (TZ §4): SSE oqimi — yo'nalishlar, manbalar (yo'nalish bo'yicha guruhlangan), javob matni,
 * deterministik tekshiruv natijasi. Har bir savol Claude API ni chaqiradi va savol kvotasini band qiladi.
 */
import { ask, type ChatSource, type Verification } from "@mezon/api-client";
import { LANGUAGES } from "@mezon/i18n";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircleIcon, ArrowRightIcon, CrownIcon, SendHorizontalIcon, SquareIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, Badge, Button, Card, CiteChip, cn, CustomSelect, DatePicker, FadeIn, Spinner, staggerStyle, useLanguage } from "@mezon/web-kit";

import { Markdown } from "@/components/legal/markdown";
import { keys, notifyError, useUsage } from "@/lib/queries";

interface Turn {
  id: number;
  question: string;
  status: string;
  sources: ChatSource[];
  text: string;
  verification?: Verification;
  error?: string;
  streaming: boolean;
}

type Effort = "low" | "medium" | "high";

function SourceGroups({ sources }: { sources: ChatSource[] }) {
  const { t } = useTranslation();
  const groups = new Map<string, ChatSource[]>();
  for (const s of sources) {
    const topic = s.topic || t("Manbalar");
    groups.set(topic, [...(groups.get(topic) ?? []), s]);
  }
  return (
    <div className="mb-5 flex flex-col gap-3">
      {[...groups].map(([topic, items]) => (
        <div key={topic} className="flex flex-wrap items-center gap-1.5">
          <div className="w-full text-[13px] font-medium text-muted">{topic}</div>
          {items.map((s) => (
            <CiteChip key={s.key} href={s.lex_url}
              title={`${s.doc_title} · ${t("tahrir")} ${s.edition}${s.as_of?.note ? ` · ${s.as_of.note}` : ""}`}>
              <b className="mr-1 font-semibold">{s.key}</b>
              {s.label}
              {s.as_of?.state === "changed" && <span className="text-amber"> · {t("oʻsha sanadagi tahrir")}</span>}
              {s.as_of?.state === "unknown" && <span className="text-muted"> · {t("sanadagi tahrir nomaʼlum")}</span>}
            </CiteChip>
          ))}
        </div>
      ))}
    </div>
  );
}

function VerificationBlock({ v }: { v: Verification }) {
  const { t } = useTranslation();
  return (
    <div className="mt-5 border-t border-line pt-4 text-[13px]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={v.ok ? "ok" : "bad"}>{v.ok ? t("✓ Tekshiruvdan oʻtdi") : t("⚠ Xato topildi")}</Badge>
        <span className="text-muted">
          {t("tekshirilgan iqtiboslar:")} {v.quotes_checked}
        </span>
      </div>
      {v.issues.map((issue, i) => (
        <div key={i} className={cn("mt-2", issue.severity === "error" ? "text-red" : issue.severity === "warning" ? "text-amber" : "text-muted")}>
          {issue.detail}
        </div>
      ))}
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const { t } = useTranslation();
  const sources = Object.fromEntries(turn.sources.map((s) => [s.key, s]));
  const ctx = {
    sources,
    verified: !!turn.verification,
    cited: new Set(turn.verification?.citations ?? []),
    missingTitle: t("Bunday manba berilmagan"),
  };
  return (
    <FadeIn className="flex flex-col gap-4">
      <div className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-3 text-primary-foreground">{turn.question}</div>
      <Card className="px-6 py-5">
        {(turn.error || turn.streaming) && (
          <div className={cn("mb-3 flex items-center gap-2 text-[13px]", turn.error ? "text-red" : "text-muted")}>
            {!turn.error && <Spinner className="size-3.5" />}
            {turn.error ?? turn.status}
          </div>
        )}
        {turn.sources.length > 0 && <SourceGroups sources={turn.sources} />}
        <Markdown text={turn.text} ctx={ctx} className={cn("leading-[1.75]", turn.streaming && "cursor-blink")} />
        {turn.verification && <VerificationBlock v={turn.verification} />}
      </Card>
    </FadeIn>
  );
}

export function ChatPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [answerLang, setAnswerLang] = useState<string>(language);
  const [onDate, setOnDate] = useState("");
  const [effort, setEffort] = useState<Effort>("medium");
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = turns.some((x) => x.streaming);

  const usage = useUsage();
  const u = usage.data;
  const chatUsage = u?.usage.find((r) => r.kind === "chat") ?? u?.usage.find((r) => r.label.toLowerCase().includes("savol"));
  const chatExhausted = !u?.unlimited && !!chatUsage && chatUsage.used >= chatUsage.limit;
  const chatRemaining = u?.unlimited ? null : chatUsage ? Math.max(0, chatUsage.limit - chatUsage.used) : null;

  useEffect(() => {
    setAnswerLang(language);
  }, [language]);
  // Sahifadan chiqilsa oqim to'xtatiladi (aks holda fonda pullik javob va kvota sarfi davom etardi)
  useEffect(() => () => abortRef.current?.abort(), []);
  // Effekt hech narsa qaytarmasin: yangi brauzerlarda scrollIntoView Promise qaytaradi (React uni cleanup deb chaqiradi)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length]);

  const examples = [
    t("Aldab pul olgan odamga qanday jazo beriladi?"),
    t("Gumon qilinuvchini necha soatgacha ushlab turish mumkin?"),
    t("Ish beruvchi xodimni qanday asoslarda ishdan boʻshatishi mumkin?"),
  ];

  async function send(text: string) {
    if (chatExhausted) {
      navigate("/billing");
      return;
    }
    const q = text.trim();
    if (!q || busy) return;
    const id = Date.now();
    const update = (patch: Partial<Turn> | ((turn: Turn) => Partial<Turn>)) =>
      setTurns((all) => all.map((x) => (x.id === id ? { ...x, ...(typeof patch === "function" ? patch(x) : patch) } : x)));
    setTurns((all) => [...all, { id, question: q, status: t("Qidirilmoqda…"), sources: [], text: "", streaming: true }]);
    setQuestion("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await ask(api, { question: q, lang: answerLang, effort, on_date: onDate || null }, {
        aspects: (list) => update({ status: t("{{n}} ta yoʻnalish: {{topics}} · qidirilmoqda…", { n: list.length, topics: list.map((a) => a.topic).join(" · ") }) }),
        sources: (list) => update({ sources: list, status: t("{{n}} ta manba topildi · javob yozilmoqda…", { n: list.length }) }),
        delta: (chunk) => update((x) => ({ text: x.text + chunk })),
        reset: () => update({ text: "" }),
        verification: (v) => update({ verification: v }),
        done: () => update({ status: t("Tayyor") }),
        error: (message) => update({ error: message }),
        incomplete: () => update({ status: "", error: t("Aloqa uzildi: javob toʻliq emas va tekshirilmagan. Savolni qayta yuboring.") }),
      }, controller.signal);
    } catch (err) {
      if (controller.signal.aborted) update({ status: t("Toʻxtatildi") });
      else {
        update({ error: err instanceof Error && "status" in err ? err.message : t("Server bilan aloqa uzildi.") });
        notifyError(err, t, () => navigate("/billing"));
      }
    } finally {
      update({ streaming: false });
      abortRef.current = null;
      void queryClient.invalidateQueries({ queryKey: keys.usage });
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void send(question);
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-8rem)] max-w-3xl flex-col px-5 pt-8 lg:min-h-dvh">
      <div className="flex-1 space-y-8 pb-6">
        {turns.length === 0 ? (
          <FadeIn className="mt-[10vh]">
            <h1 className="text-center font-serif text-[30px] font-semibold leading-tight sm:text-[36px]">{t("Oʻzbekiston qonunchiligi boʻyicha savol bering")}</h1>
            <p className="mx-auto mt-3 max-w-xl text-center text-[15px] text-muted">{t("Javob lex.uz dagi amaldagi moddalarga tayanadi, har bir iqtibos manba bilan solishtiriladi.")}</p>
            <div className="mt-10 grid gap-3 sm:grid-cols-3">
              {examples.map((ex, i) => (
                <button key={ex} onClick={() => void send(ex)} style={staggerStyle(i, 80)}
                  className="animate-in-up group flex flex-col justify-between gap-4 rounded-xl border border-line bg-surface p-4 text-left text-[14px] leading-snug shadow-card transition-colors hover:border-primary/40">
                  {ex}
                  <ArrowRightIcon className="size-4 text-muted transition-colors group-hover:text-primary" aria-hidden />
                </button>
              ))}
            </div>
          </FadeIn>
        ) : (
          turns.map((turn) => <TurnView key={turn.id} turn={turn} />)
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="sticky bottom-[4.5rem] bg-gradient-to-t from-canvas from-70% to-transparent pb-4 pt-6 lg:bottom-0">
        <div className="rounded-2xl border border-line bg-surface p-3 shadow-card focus-within:border-primary/50 focus-within:shadow-glow">
          {chatExhausted && (
            <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber/40 bg-amber/10 px-3.5 py-2 text-xs text-ink">
              <div className="flex items-center gap-1.5">
                <AlertCircleIcon className="size-4 shrink-0 text-amber" />
                <span className="font-semibold text-amber">{t("Savol limitingiz tugadi:")}</span>
                <span className="text-muted">
                  {u?.plan === "FREE"
                    ? t("Bepul tarifda jami {{lim}} ta savol berish mumkin.", { lim: chatUsage?.limit ?? 3 })
                    : t("Kunlik savol limitingiz ({{lim}} ta) tugadi.", { lim: chatUsage?.limit ?? 100 })}
                </span>
              </div>
              <Button type="button" variant="gold" size="sm" onClick={() => navigate("/billing")} className="h-7 px-2.5 text-xs">
                <CrownIcon className="size-3.5" /> {t("Pro tarifiga oʻtish")}
              </Button>
            </div>
          )}
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={chatExhausted}
            maxLength={2000}
            rows={2}
            placeholder={chatExhausted ? t("Savol limitingiz tugagan. Davom etish uchun Pro tarifiga oʻting.") : t("Savolingizni yozing…")}
            aria-label={t("Savolingizni yozing…")}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!chatExhausted) void send(question);
              }
            }}
            className="max-h-40 w-full resize-none bg-transparent px-2 py-1 text-[16px] outline-none placeholder:text-muted/70 disabled:opacity-60"
          />
          <div className="flex flex-wrap items-center gap-2 px-1">
            <CustomSelect
              value={answerLang}
              onValueChange={setAnswerLang}
              title={t("Javob tili")}
              aria-label={t("Javob tili")}
              size="sm"
              className="h-8 w-auto min-w-[124px] bg-subtle border-transparent hover:border-line hover:bg-subtle/80"
              options={LANGUAGES.map((l) => ({ value: l.code, label: l.name }))}
            />
            <DatePicker
              value={onDate}
              onChange={setOnDate}
              size="sm"
              title={t("Voqea sanasi (ixtiyoriy): qonun shu sanadagi tahrirda olinadi")}
              aria-label={t("Voqea sanasi (ixtiyoriy): qonun shu sanadagi tahrirda olinadi")}
              placeholder={t("Sana")}
            />
            <CustomSelect
              value={effort}
              onValueChange={(v) => setEffort(v as Effort)}
              title={t("Tahlil chuqurligi")}
              aria-label={t("Tahlil chuqurligi")}
              size="sm"
              className="h-8 w-auto min-w-[85px] bg-subtle border-transparent hover:border-line hover:bg-subtle/80"
              options={[
                { value: "low", label: t("tez") },
                { value: "medium", label: t("oʻrta") },
                { value: "high", label: t("chuqur") },
              ]}
            />
            {u && (
              <div
                className={cn(
                  "flex h-8 shrink-0 items-center gap-1 rounded-lg px-2 text-[12px] font-medium tabular-nums",
                  u.unlimited
                    ? "bg-subtle text-muted"
                    : chatExhausted
                      ? "bg-red/10 text-red"
                      : chatRemaining !== null && chatRemaining <= 1
                        ? "bg-amber/10 text-amber"
                        : "bg-subtle text-muted",
                )}
                title={u.unlimited ? t("Cheklovsiz savol-javob") : t("Qolgan savollar soni")}
              >
                <span>
                  {u.unlimited
                    ? t("Cheklovsiz")
                    : chatRemaining !== null
                      ? t("Savollar: {{rem}}/{{lim}}", { rem: chatRemaining, lim: chatUsage?.limit ?? 0 })
                      : u.plan_name}
                </span>
              </div>
            )}
            <span className="ml-auto text-xs tabular-nums text-muted">{question.length > 1500 ? `${question.length}/2000` : ""}</span>
            {chatExhausted ? (
              <Button type="button" variant="gold" size="sm" onClick={() => navigate("/billing")} className="rounded-xl">
                <CrownIcon className="size-4" /> {t("Tarifni yangilash")}
              </Button>
            ) : busy ? (
              <Button type="button" variant="outline" size="sm" onClick={() => abortRef.current?.abort()}>
                <SquareIcon /> {t("Toʻxtatish")}
              </Button>
            ) : (
              <Button type="submit" disabled={!question.trim()} className="rounded-xl">
                <SendHorizontalIcon /> {t("Yuborish")}
              </Button>
            )}
          </div>
        </div>
        <p className="mt-2 text-center text-xs text-muted">{t("Maʼlumot tanishish uchun. Yakuniy huquqiy xulosani advokat beradi.")}</p>
      </form>
    </div>
  );
}
