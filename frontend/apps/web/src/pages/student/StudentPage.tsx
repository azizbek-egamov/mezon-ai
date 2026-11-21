import {
  api,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
  Input,
  Label,
  PageHeader,
  saveBlob,
  Spinner,
  Textarea,
  useLanguage,
} from "@mezon/web-kit";
import {
  AwardIcon,
  BookMarkedIcon,
  BookOpenIcon,
  CalculatorIcon,
  CalendarIcon,
  CheckCircle2Icon,
  DownloadIcon,
  ExternalLinkIcon,
  FileDiffIcon,
  GavelIcon,
  GraduationCapIcon,
  PresentationIcon,
  RefreshCwIcon,
  ScaleIcon,
  SearchIcon,
  SparklesIcon,
  XCircleIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

interface CaseItem {
  id: number;
  title: string;
  category: string;
  category_label: string;
  difficulty: string;
  difficulty_label: string;
  facts: string;
  task_question: string;
  relevant_laws: Array<{ law: string; article: number | string; title: string }>;
  reference_solution?: {
    issue: string;
    rule: string;
    analysis: string;
    conclusion: string;
  };
}

interface RetrievedArticle {
  article_id: number;
  document_id: number;
  doc_title: string;
  label: string;
  lex_url: string;
  score: number;
}

interface IracSolution {
  title?: string;
  issue: string;
  rules: string;
  analysis: string;
  conclusion: string;
  action_steps?: string[];
  student_assessment?: {
    evaluated: boolean;
    score: number | null;
    strengths: string;
    mistakes: string;
    recommendations: string;
  };
  retrieved_articles?: RetrievedArticle[];
}

interface QuizOption {
  key: string;
  text: string;
}

interface QuizQuestion {
  id: number;
  category: string;
  category_label: string;
  question_text: string;
  options: QuizOption[];
  law_reference?: string;
}

interface QuizResultDetail {
  question_id: number;
  question_text: string;
  selected_option: string;
  correct_option: string;
  is_correct: boolean;
  explanation: string;
  law_reference: string;
}

interface QuizResult {
  total_questions: number;
  correct_count: number;
  percentage: number;
  passed: boolean;
  details: QuizResultDetail[];
}

interface GlossaryItem {
  id: number;
  term: string;
  latin_term: string;
  category: string;
  category_label: string;
  is_roman_latin: boolean;
  definition: string;
  legal_source: string;
  example_usage: string;
}

interface CourtFeeResult {
  court_type: string;
  claim_type: string;
  bhm_rate: number;
  claim_amount: number;
  court_fee_uzs: number;
  postal_cost_uzs: number;
  total_uzs: number;
  legal_basis: string;
}

interface DeadlineResult {
  start_date: string;
  deadline_date: string;
  procedure: string;
  rule_description: string;
  adjusted_for_weekend: boolean;
}

interface MootCourtResult {
  case_summary?: string;
  plaintiff: {
    position: string;
    legal_grounds: string[];
    key_arguments: string[];
    court_speech: string;
  };
  defendant: {
    position: string;
    counter_arguments: string[];
    objections: string[];
    defense_speech: string;
  };
  judge: {
    burden_of_proof: string;
    decisive_questions: string[];
    probable_outcome: string;
  };
  relevant_articles?: RetrievedArticle[];
}

interface ThesisResult {
  topic: string;
  work_type_label: string;
  relevance: string;
  object_and_subject: string;
  goal_and_tasks: string;
  outline: Array<{
    section: string;
    title: string;
    subsections: string[];
  }>;
  regulatory_framework: string[];
  recommended_literature: string[];
}

type TabType = "cases" | "presentations" | "diff" | "quiz" | "calculator" | "glossary" | "moot_court" | "thesis";

export function StudentPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [tab, setTab] = useState<TabType>("cases");

  // 1. Kazuslar holati
  const [caseBank, setCaseBank] = useState<CaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseItem | null>(null);
  const [customFacts, setCustomFacts] = useState("");
  const [customQuestion, setCustomQuestion] = useState("");
  const [studentAnswer, setStudentAnswer] = useState("");
  const [caseBusy, setCaseBusy] = useState(false);
  const [caseResult, setCaseResult] = useState<IracSolution | null>(null);

  // 2. Taqdimotlar holati
  const [presentationTopic, setPresentationTopic] = useState("");
  const [slideCount, setSlideCount] = useState(5);
  const [presentationBusy, setPresentationBusy] = useState(false);
  const [outlineResult, setOutlineResult] = useState<any | null>(null);
  const [downloadingPptx, setDownloadingPptx] = useState(false);

  // 3. Diff holati
  const [textA, setTextA] = useState("");
  const [textB, setTextB] = useState("");
  const [diffBusy, setDiffBusy] = useState(false);
  const [diffResult, setDiffResult] = useState<{
    similarity_ratio: number;
    stats: { added_words: number; deleted_words: number; unchanged_words: number };
    diff_segments: Array<{ type: "equal" | "insert" | "delete"; text: string }>;
  } | null>(null);

  // 4. Test holati
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [quizBusy, setQuizBusy] = useState(false);
  const [quizSubmitting, setQuizSubmitting] = useState(false);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [quizCategory, setQuizCategory] = useState("ALL");

  // 5. Kalkulyator holati
  const [calcTab, setCalcTab] = useState<"court_fee" | "deadline">("court_fee");
  const [courtType, setCourtType] = useState<"CIVIL" | "ECONOMIC" | "ADMINISTRATIVE">("CIVIL");
  const [claimType, setClaimType] = useState<"PROPERTY" | "NON_PROPERTY" | "DIVORCE" | "ORDER" | "CONTRACT_DISPUTE">("PROPERTY");
  const [claimAmount, setClaimAmount] = useState<string>("50000000");
  const [isRepeatedDivorce, setIsRepeatedDivorce] = useState(false);
  const [courtFeeResult, setCourtFeeResult] = useState<CourtFeeResult | null>(null);
  const [feeBusy, setFeeBusy] = useState(false);

  const [procedure, setProcedure] = useState("CIVIL_APPEAL");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [deadlineResult, setDeadlineResult] = useState<DeadlineResult | null>(null);
  const [deadlineBusy, setDeadlineBusy] = useState(false);

  // 6. Glossariy holati
  const [glossaryQuery, setGlossaryQuery] = useState("");
  const [glossaryCategory, setGlossaryCategory] = useState("ALL");
  const [onlyRomanLatin, setOnlyRomanLatin] = useState(false);
  const [glossaryItems, setGlossaryItems] = useState<GlossaryItem[]>([]);
  const [glossaryBusy, setGlossaryBusy] = useState(false);

  // 7. Sud simulyatsiyasi (Moot Court)
  const [mootFacts, setMootFacts] = useState("");
  const [mootClaim, setMootClaim] = useState("");
  const [mootBusy, setMootBusy] = useState(false);
  const [mootResult, setMootResult] = useState<MootCourtResult | null>(null);

  // 8. BMI & Kurs ishi
  const [thesisTopic, setThesisTopic] = useState("");
  const [thesisWorkType, setThesisWorkType] = useState<"COURSEWORK" | "THESIS_BACHELOR" | "MASTER_DISSERTATION">("COURSEWORK");
  const [thesisBusy, setThesisBusy] = useState(false);
  const [thesisResult, setThesisResult] = useState<ThesisResult | null>(null);

  useEffect(() => {
    // Kazuslar bankini yuklash
    void api.raw("/student/cases/bank").then(async (res) => {
      if (res.ok) {
        const data = (await res.json()) as CaseItem[];
        setCaseBank(data);
      }
    });

    // Test savollarini yuklash
    loadQuizQuestions(quizCategory);

    // Glossariyni yuklash
    loadGlossary();
  }, []);

  function loadQuizQuestions(cat: string) {
    setQuizBusy(true);
    setQuizResult(null);
    setUserAnswers({});
    const url = cat && cat !== "ALL" ? `/student/quiz/questions?category=${cat}` : "/student/quiz/questions";
    void api.raw(url).then(async (res) => {
      if (res.ok) {
        const data = await res.json();
        setQuizQuestions(data.questions || []);
      }
      setQuizBusy(false);
    });
  }

  function loadGlossary(q = glossaryQuery, cat = glossaryCategory, latin = onlyRomanLatin) {
    setGlossaryBusy(true);
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (cat && cat !== "ALL") params.set("category", cat);
    if (latin) params.set("is_roman_latin", "true");

    void api.raw(`/student/glossary?${params.toString()}`).then(async (res) => {
      if (res.ok) {
        const data = (await res.json()) as GlossaryItem[];
        setGlossaryItems(data);
      }
      setGlossaryBusy(false);
    });
  }

  // Kazusni tanlash
  function selectPresetCase(item: CaseItem) {
    setSelectedCase(item);
    setCustomFacts(item.facts);
    setCustomQuestion(item.task_question);
    setStudentAnswer("");
    setCaseResult(null);
  }

  // Kazusni hal qilish
  async function handleSolveCase() {
    if (!customFacts.trim()) {
      toast.error(t("Iltimos, kazus faktlarini kiriting"));
      return;
    }
    setCaseBusy(true);
    try {
      const payload = {
        facts: customFacts,
        task_question: customQuestion,
        student_answer: studentAnswer,
        case_bank_id: selectedCase?.id,
        lang: language === "ru" ? "ru" : language === "uz-Cyrl" ? "cyr" : language === "kaa" ? "kaa" : language === "en" ? "en" : "lat",
      };

      const res = await api.raw("/student/cases/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || err.message || "Tahlil jarayonida xatolik");
      }

      const data = (await res.json()) as IracSolution;
      setCaseResult(data);
      toast.success(t("Kazus muvaffaqiyatli tahlil qilindi"));
    } catch (e: any) {
      toast.error(e.message || t("Server xatosi"));
    } finally {
      setCaseBusy(false);
    }
  }

  // Taqdimot rejasini generatsiya qilish
  async function handleGenerateOutline() {
    if (!presentationTopic.trim()) {
      toast.error(t("Iltimos, taqdimot mavzusini kiriting"));
      return;
    }
    setPresentationBusy(true);
    try {
      const res = await api.raw("/student/presentations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: presentationTopic,
          slide_count: slideCount,
          download: false,
        }),
      });

      if (!res.ok) throw new Error("Reja generatsiya qilishda xatolik");

      const data = await res.json();
      setOutlineResult(data.outline);
      toast.success(t("Taqdimot rejasi tayyor"));
    } catch {
      toast.error(t("Taqdimot tayyorlashda xatolik"));
    } finally {
      setPresentationBusy(false);
    }
  }

  // PPTX faylni yuklab olish
  async function handleDownloadPptx() {
    if (!presentationTopic.trim()) return;
    setDownloadingPptx(true);
    try {
      const res = await api.raw("/student/presentations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: presentationTopic,
          slide_count: slideCount,
          download: true,
        }),
      });

      if (!res.ok) throw new Error("Yuklab olishda xatolik");

      const blob = await res.blob();
      const safeName = presentationTopic.slice(0, 30).replace(/[^a-zA-Z0-9а-яА-ЯёЁўқғҳЎҚҒҲ]/g, "_");
      saveBlob(blob, `Mezon_${safeName || "Taqdimot"}.pptx`);
      toast.success(t("Taqdimot yuklab olindi"));
    } catch {
      toast.error(t("Faylni yuklab olishda xatolik"));
    } finally {
      setDownloadingPptx(false);
    }
  }

  // Qonunlar diff taqqoslash
  async function handleCompareDiff() {
    if (!textA.trim() && !textB.trim()) {
      toast.error(t("Taqqoslash uchun matn kiritilishi kerak"));
      return;
    }
    setDiffBusy(true);
    try {
      const res = await api.raw("/student/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text_a: textA, text_b: textB }),
      });
      if (!res.ok) throw new Error("Diff error");
      const data = await res.json();
      setDiffResult(data);
    } catch {
      toast.error(t("Taqqoslashda xatolik"));
    } finally {
      setDiffBusy(false);
    }
  }

  // Test javoblarini topshirish
  async function handleSubmitQuiz() {
    const answers = Object.entries(userAnswers).map(([qid, opt]) => ({
      question_id: Number(qid),
      selected_option: opt,
    }));
    if (answers.length === 0) {
      toast.error(t("Kamida bitta savolga javob belgilang"));
      return;
    }
    setQuizSubmitting(true);
    try {
      const res = await api.raw("/student/quiz/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      if (!res.ok) throw new Error("Quiz submit error");
      const data = (await res.json()) as QuizResult;
      setQuizResult(data);
      toast.success(t("Test natijalari hisoblandi"));
    } catch {
      toast.error(t("Testni topshirishda xatolik"));
    } finally {
      setQuizSubmitting(false);
    }
  }

  // Davlat boji hisoblash
  async function handleCalculateCourtFee() {
    setFeeBusy(true);
    try {
      const res = await api.raw("/student/calculator/court-fee", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          court_type: courtType,
          claim_type: claimType,
          claim_amount: parseFloat(claimAmount) || 0,
          is_repeated_divorce: isRepeatedDivorce,
        }),
      });
      if (!res.ok) throw new Error("Calculation error");
      const data = (await res.json()) as CourtFeeResult;
      setCourtFeeResult(data);
      toast.success(t("Davlat boji hisoblandi"));
    } catch {
      toast.error(t("Hisoblashda xatolik"));
    } finally {
      setFeeBusy(false);
    }
  }

  // Protsessual muddat hisoblash
  async function handleCalculateDeadline() {
    setDeadlineBusy(true);
    try {
      const res = await api.raw("/student/calculator/procedural-deadline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          procedure,
          start_date: startDate,
        }),
      });
      if (!res.ok) throw new Error("Calculation error");
      const data = (await res.json()) as DeadlineResult;
      setDeadlineResult(data);
      toast.success(t("Muddat hisoblandi"));
    } catch {
      toast.error(t("Muddatni hisoblashda xatolik"));
    } finally {
      setDeadlineBusy(false);
    }
  }

  // Sud simulyatsiyasi (Moot Court)
  async function handleSimulateMootCourt() {
    if (!mootFacts.trim()) {
      toast.error(t("Iltimos, ish faktlarini kiriting"));
      return;
    }
    setMootBusy(true);
    try {
      const res = await api.raw("/student/moot-court/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_facts: mootFacts,
          claim_dispute: mootClaim,
          lang: language === "ru" ? "ru" : language === "uz-Cyrl" ? "cyr" : language === "kaa" ? "kaa" : language === "en" ? "en" : "lat",
        }),
      });
      if (!res.ok) throw new Error("Simulation error");
      const data = (await res.json()) as MootCourtResult;
      setMootResult(data);
      toast.success(t("Sud simulyatsiyasi tayyor"));
    } catch (e: any) {
      toast.error(e.message || t("Simulyatsiyada xatolik"));
    } finally {
      setMootBusy(false);
    }
  }

  // BMI / Kurs ishi rejasi
  async function handleBuildThesisRoadmap() {
    if (!thesisTopic.trim()) {
      toast.error(t("Iltimos, ilmiy ish mavzusini kiriting"));
      return;
    }
    setThesisBusy(true);
    try {
      const res = await api.raw("/student/thesis/roadmap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: thesisTopic,
          work_type: thesisWorkType,
          lang: language === "ru" ? "ru" : language === "uz-Cyrl" ? "cyr" : language === "kaa" ? "kaa" : language === "en" ? "en" : "lat",
        }),
      });
      if (!res.ok) throw new Error("Roadmap error");
      const data = (await res.json()) as ThesisResult;
      setThesisResult(data);
      toast.success(t("Tadqiqot rejasi tayyorlandi"));
    } catch (e: any) {
      toast.error(e.message || t("Reja tuzishda xatolik"));
    } finally {
      setThesisBusy(false);
    }
  }

  const navTabs = [
    { key: "cases" as const, label: t("Kazuslar ustaxonasi"), icon: ScaleIcon },
    { key: "presentations" as const, label: t("Yuridik taqdimotlar"), icon: PresentationIcon },
    { key: "diff" as const, label: t("Qonunlar qiyosi"), icon: FileDiffIcon },
    { key: "quiz" as const, label: t("Imtihon trenajyori"), icon: AwardIcon },
    { key: "calculator" as const, label: t("Kalkulyator"), icon: CalculatorIcon },
    { key: "glossary" as const, label: t("Yuridik lugʻat"), icon: BookMarkedIcon },
    { key: "moot_court" as const, label: t("Sud simulyatsiyasi"), icon: GavelIcon },
    { key: "thesis" as const, label: t("BMI & Kurs ishi"), icon: GraduationCapIcon },
  ];

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <PageHeader
            title={t("Akademiya (Talabalar)")}
            description={t("Huquqshunos talabalar, magistrlar va amaliyotchilar uchun ixtisoslashgan yuridik ustaxona")}
          />
        </div>
        <Badge tone="info" className="flex w-fit items-center gap-1.5 py-1">
          <GraduationCapIcon className="size-4 shrink-0" />
          <span>TDYU & Yuridik OTMlar standarti</span>
        </Badge>
      </div>

      {/* Navigatsion Tablar — 8 ta modul */}
      <div className="grid grid-cols-2 gap-1.5 rounded-xl bg-subtle p-1.5 sm:grid-cols-4 lg:grid-cols-8">
        {navTabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-2.5 text-xs font-medium whitespace-nowrap transition-[background,color,box-shadow,transform] active:scale-[0.98]",
              tab === key
                ? "bg-surface text-ink shadow-card font-semibold"
                : "text-muted hover:text-ink hover:bg-surface/50"
            )}
          >
            <Icon className={cn("size-3.5 shrink-0", tab === key ? "text-primary" : "text-muted")} />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>

      {/* 1. KAZUSLAR USTAXONASI */}
      {tab === "cases" && (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Chap ustun: Namunaviy kazuslar banki */}
          <div className="flex flex-col gap-4 lg:col-span-4">
            <Card className="flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base font-semibold">
                  <BookOpenIcon className="size-4 text-primary" />
                  {t("Namunaviy kazuslar banki")}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedCase(null);
                    setCustomFacts("");
                    setCustomQuestion("");
                    setStudentAnswer("");
                    setCaseResult(null);
                  }}
                  className={cn(
                    "flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-all",
                    !selectedCase
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/40 bg-surface"
                  )}
                >
                  <span className="text-sm font-semibold flex items-center gap-1.5">
                    <SparklesIcon className="size-3.5" />
                    {t("Yangi (Shaxsiy) kazus kiritish")}
                  </span>
                  <span className="text-xs text-muted">
                    {t("Oʻzingizning kazusingiz yoki mustaqil ish topshirigʻingizni tekshiring")}
                  </span>
                </button>

                <div className="my-1 border-t border-border" />

                {caseBank.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectPresetCase(item)}
                    className={cn(
                      "flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-all",
                      selectedCase?.id === item.id
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border hover:border-primary/30 bg-surface"
                    )}
                  >
                    <div className="flex w-full items-center justify-between gap-2">
                      <span className="text-xs font-medium text-primary">
                        {item.category_label}
                      </span>
                      <span className="rounded bg-subtle px-1.5 py-0.5 text-[10px] text-muted">
                        {item.difficulty_label}
                      </span>
                    </div>
                    <span className="text-sm font-medium leading-snug text-ink line-clamp-2">
                      {item.title}
                    </span>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* O'ng ustun: Kazus yechish va IRAC tahlili */}
          <div className="flex flex-col gap-6 lg:col-span-8">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <ScaleIcon className="size-4 text-primary" />
                  {selectedCase ? selectedCase.title : t("Kazus parametrlari va talaba yechimi")}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <Label htmlFor="case-facts" className="text-xs font-semibold uppercase text-muted">
                    {t("Kazus holati (Faktlar)")}
                  </Label>
                  <Textarea
                    id="case-facts"
                    rows={4}
                    value={customFacts}
                    onChange={(e) => setCustomFacts(e.target.value)}
                    placeholder={t("Kazus tafsilotlarini batafsil yozing...")}
                    className="mt-1.5 resize-y text-sm"
                  />
                </div>

                <div>
                  <Label htmlFor="case-q" className="text-xs font-semibold uppercase text-muted">
                    {t("Hal qilinishi lozim boʻlgan savol (Talab)")}
                  </Label>
                  <Input
                    id="case-q"
                    value={customQuestion}
                    onChange={(e) => setCustomQuestion(e.target.value)}
                    placeholder={t("Masalan: Bitim haqiqiy deb topilishi mumkinmi?")}
                    className="mt-1.5 text-sm"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="student-answer" className="text-xs font-semibold uppercase text-muted">
                      {t("Sizning taklif qilayotgan yechimingiz (ixtiyoriy)")}
                    </Label>
                    <span className="text-xs text-primary font-medium">
                      {t("AI tekshirishi va baholashi uchun")}
                    </span>
                  </div>
                  <Textarea
                    id="student-answer"
                    rows={3}
                    value={studentAnswer}
                    onChange={(e) => setStudentAnswer(e.target.value)}
                    placeholder={t("Oʻz fikringiz va taxminiy huquqiy yechimingizni yozing. AI sizning yechimingizga xolis taqriz beradi...")}
                    className="mt-1.5 resize-y text-sm"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <Button onClick={handleSolveCase} disabled={caseBusy || !customFacts.trim()}>
                    {caseBusy ? <Spinner className="size-4" /> : <SparklesIcon className="size-4" />}
                    <span>{t("IRAC uslubida tahlil qilish")}</span>
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* IRAC TAHLIL NATIJASI */}
            {caseResult && (
              <div className="flex flex-col gap-4">
                {/* Agar talaba javob bergan bo'lsa: Baholash kartasi */}
                {caseResult.student_assessment?.evaluated && (
                  <Card className="border-primary/30 bg-primary/5">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-semibold flex items-center gap-2 text-primary">
                          <AwardIcon className="size-5" />
                          {t("Talaba javobiga taqriz va baho")}
                        </CardTitle>
                        {caseResult.student_assessment.score !== null && (
                          <div className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-sm font-bold text-primary-foreground shadow-sm">
                            <span>{caseResult.student_assessment.score} / 100</span>
                          </div>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-2.5 text-sm">
                      {caseResult.student_assessment.strengths && (
                        <div>
                          <strong className="text-emerald-700 dark:text-emerald-400">
                            {t("Kuchli tomonlari:")}
                          </strong>{" "}
                          <span>{caseResult.student_assessment.strengths}</span>
                        </div>
                      )}
                      {caseResult.student_assessment.mistakes && (
                        <div>
                          <strong className="text-amber-700 dark:text-amber-400">
                            {t("Xatolar va kamchiliklar:")}
                          </strong>{" "}
                          <span>{caseResult.student_assessment.mistakes}</span>
                        </div>
                      )}
                      {caseResult.student_assessment.recommendations && (
                        <div>
                          <strong className="text-primary">
                            {t("Tavsiyalar:")}
                          </strong>{" "}
                          <span>{caseResult.student_assessment.recommendations}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* IRAC Bosqichlari */}
                <div className="grid gap-3">
                  {/* I - Issue */}
                  <Card className="border-l-4 border-l-blue-500">
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 font-semibold text-blue-600 dark:text-blue-400">
                        <span className="flex size-6 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
                          I
                        </span>
                        <span>{t("Issue — Huquqiy muammo")}</span>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-ink">
                        {caseResult.issue}
                      </p>
                    </CardContent>
                  </Card>

                  {/* R - Rule */}
                  <Card className="border-l-4 border-l-purple-500">
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 font-semibold text-purple-600 dark:text-purple-400">
                        <span className="flex size-6 items-center justify-center rounded-full bg-purple-100 text-xs font-bold text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                          R
                        </span>
                        <span>{t("Rule — Amaldagi huquqiy norma")}</span>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-ink whitespace-pre-line">
                        {caseResult.rules}
                      </p>
                    </CardContent>
                  </Card>

                  {/* A - Analysis */}
                  <Card className="border-l-4 border-l-amber-500">
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 font-semibold text-amber-600 dark:text-amber-400">
                        <span className="flex size-6 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
                          A
                        </span>
                        <span>{t("Analysis — Qonunni faktlarga tatbiq etish (Tahlil)")}</span>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-ink whitespace-pre-line">
                        {caseResult.analysis}
                      </p>
                    </CardContent>
                  </Card>

                  {/* C - Conclusion */}
                  <Card className="border-l-4 border-l-emerald-500">
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 font-semibold text-emerald-600 dark:text-emerald-400">
                        <span className="flex size-6 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                          C
                        </span>
                        <span>{t("Conclusion — Sud yoki amaliy xulosa")}</span>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-ink font-medium">
                        {caseResult.conclusion}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                {/* Qdrant orqali topilgan tegishli qonun moddalari */}
                {caseResult.retrieved_articles && caseResult.retrieved_articles.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-semibold flex items-center gap-2">
                        <BookOpenIcon className="size-4 text-primary" />
                        {t("Tegishli qonun moddalari (Lex.uz havolalari)")}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2 sm:grid-cols-2">
                      {caseResult.retrieved_articles.map((art) => (
                        <a
                          key={art.article_id}
                          href={art.lex_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-start justify-between gap-2 rounded-lg border border-border p-3 text-sm transition-all hover:border-primary/50 hover:bg-subtle"
                        >
                          <div>
                            <span className="font-semibold text-ink line-clamp-1">
                              {art.doc_title}
                            </span>
                            <span className="text-xs text-primary font-medium">
                              {art.label}
                            </span>
                          </div>
                          <ExternalLinkIcon className="size-3.5 shrink-0 text-muted" />
                        </a>
                      ))}
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. YURIDIK TAQDIMOTLAR (.PPTX) */}
      {tab === "presentations" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="flex flex-col gap-4 lg:col-span-5">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <PresentationIcon className="size-4 text-primary" />
                  {t("Taqdimot mavzusi va parametrlari")}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <Label htmlFor="pres-topic" className="text-xs font-semibold uppercase text-muted">
                    {t("Yuridik mavzu yoki kazus")}
                  </Label>
                  <Textarea
                    id="pres-topic"
                    rows={3}
                    value={presentationTopic}
                    onChange={(e) => setPresentationTopic(e.target.value)}
                    placeholder={t("Masalan: Fuqarolik huquqida garov shartnomasining xususiyatlari")}
                    className="mt-1.5 text-sm"
                  />
                </div>

                <div>
                  <Label htmlFor="slide-count" className="text-xs font-semibold uppercase text-muted">
                    {t("Slaydlar soni")}
                  </Label>
                  <div className="mt-1.5 flex items-center gap-3">
                    {[4, 6, 8, 10].map((num) => (
                      <button
                        key={num}
                        type="button"
                        onClick={() => setSlideCount(num)}
                        className={cn(
                          "flex-1 rounded-md border py-1.5 text-xs font-medium transition-all",
                          slideCount === num
                            ? "border-primary bg-primary text-primary-foreground font-semibold"
                            : "border-border hover:bg-subtle text-ink"
                        )}
                      >
                        {num} {t("ta slayd")}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-2 flex flex-col gap-2">
                  <Button onClick={handleGenerateOutline} disabled={presentationBusy || !presentationTopic.trim()}>
                    {presentationBusy ? <Spinner className="size-4" /> : <SparklesIcon className="size-4" />}
                    <span>{t("Rejani koʻrish")}</span>
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleDownloadPptx}
                    disabled={downloadingPptx || !presentationTopic.trim()}
                    className="flex items-center gap-2"
                  >
                    {downloadingPptx ? <Spinner className="size-4" /> : <DownloadIcon className="size-4" />}
                    <span>{t("1-bosishda .pptx yuklab olish")}</span>
                  </Button>
                </div>

                <div className="rounded-lg bg-subtle p-3 text-xs text-muted leading-relaxed">
                  <strong>{t("Mezon Klassik formati:")}</strong> 16:9 zamonaviy slaydlar, toʻq koʻk Mezon korporativ uslubi, qonun moddasi va amaliy xulosalar bilan toʻliq avtomatlashtirilgan.
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-4 lg:col-span-7">
            {outlineResult ? (
              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <BookOpenIcon className="size-4 text-primary" />
                    {outlineResult.topic || presentationTopic}
                  </CardTitle>
                  <Button size="sm" onClick={handleDownloadPptx} disabled={downloadingPptx}>
                    {downloadingPptx ? <Spinner className="size-3.5" /> : <DownloadIcon className="size-3.5" />}
                    <span>{t(".pptx yuklab olish")}</span>
                  </Button>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                  {outlineResult.slides?.map((slide: any, idx: number) => (
                    <div key={idx} className="rounded-lg border border-border bg-subtle/40 p-4">
                      <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
                        <span className="text-xs font-bold text-primary uppercase tracking-wide">
                          {idx + 1}-slayd: {slide.type || "content"}
                        </span>
                        <span className="text-xs font-semibold text-ink">
                          {slide.title}
                        </span>
                      </div>
                      {slide.subtitle && (
                        <p className="mt-1.5 text-xs text-muted italic">
                          {slide.subtitle}
                        </p>
                      )}
                      {slide.points && slide.points.length > 0 && (
                        <ul className="mt-2.5 list-disc space-y-1 pl-4 text-xs text-ink leading-relaxed">
                          {slide.points.map((pt: string, pIdx: number) => (
                            <li key={pIdx}>{pt}</li>
                          ))}
                        </ul>
                      )}
                      {slide.law_reference && (
                        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-primary font-medium">
                          <ScaleIcon className="size-3.5" />
                          <span>{t("Huquqiy asos:")} {slide.law_reference}</span>
                        </div>
                      )}
                      {slide.practical_tip && (
                        <div className="mt-1 rounded bg-amber-500/10 p-2 text-xs text-amber-800 dark:text-amber-300">
                          <strong>{t("Amaliy maslahat:")}</strong> {slide.practical_tip}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : (
              <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center text-muted">
                <PresentationIcon className="size-10 text-muted/60 mb-2" />
                <p className="text-sm font-medium">{t("Mavzuni kiriting va slaydlarni koʻring yoki toʻgʻridan-toʻgʻri yuklab oling")}</p>
                <p className="text-xs text-muted mt-1">{t("Taqdimotlar OTM seminar va konferensiyalari uchun toʻliq moslashtirilgan")}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. QONUNLAR QIYOSI (DIFF - ZERO API COST) */}
      {tab === "diff" && (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <FileDiffIcon className="size-4 text-primary" />
                  {t("Yuridik matnlarni qiyosiy taqqoslash (Diff)")}
                </CardTitle>
                <Badge tone="ok" className="text-xs">
                  100% Bepul (ZERO API COST)
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="diff-a" className="text-xs font-semibold uppercase text-muted">
                    {t("Eski tahrir (A variant)")}
                  </Label>
                  <Textarea
                    id="diff-a"
                    rows={6}
                    value={textA}
                    onChange={(e) => setTextA(e.target.value)}
                    placeholder={t("Qonunning oldingi tahriri yoki boshlangʻich shartnoma matnini kiriting...")}
                    className="mt-1.5 text-xs font-mono"
                  />
                </div>
                <div>
                  <Label htmlFor="diff-b" className="text-xs font-semibold uppercase text-muted">
                    {t("Yangi tahrir (B variant)")}
                  </Label>
                  <Textarea
                    id="diff-b"
                    rows={6}
                    value={textB}
                    onChange={(e) => setTextB(e.target.value)}
                    placeholder={t("Qonunning yangi tahriri yoki oʻzgartirilgan loyihani kiriting...")}
                    className="mt-1.5 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleCompareDiff} disabled={diffBusy || (!textA.trim() && !textB.trim())}>
                  {diffBusy ? <Spinner className="size-4" /> : <FileDiffIcon className="size-4" />}
                  <span>{t("Qiyoslash")}</span>
                </Button>
              </div>
            </CardContent>
          </Card>

          {diffResult && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-semibold">
                    {t("Qiyosiy natijalar")}
                  </CardTitle>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="font-semibold text-ink">
                      {t("Oʻxshashlik:")} {(diffResult.similarity_ratio * 100).toFixed(1)}%
                    </span>
                    <span className="text-emerald-700 dark:text-emerald-400 font-semibold">
                      +{diffResult.stats.added_words} {t("ta soʻz qoʻshilgan")}
                    </span>
                    <span className="text-rose-700 dark:text-rose-400 font-semibold">
                      -{diffResult.stats.deleted_words} {t("ta soʻz oʻchirilgan")}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-border bg-subtle/30 p-4 text-xs font-mono leading-relaxed whitespace-pre-wrap">
                  {diffResult.diff_segments.map((seg, i) => {
                    if (seg.type === "insert") {
                      return (
                        <span key={i} className="bg-emerald-100 text-emerald-900 dark:bg-emerald-950/80 dark:text-emerald-200 px-0.5 rounded font-medium">
                          {seg.text}
                        </span>
                      );
                    }
                    if (seg.type === "delete") {
                      return (
                        <span key={i} className="bg-rose-100 text-rose-900 dark:bg-rose-950/80 dark:text-rose-200 line-through px-0.5 rounded opacity-75">
                          {seg.text}
                        </span>
                      );
                    }
                    return <span key={i}>{seg.text}</span>;
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 4. IMTIHON TRENAJYORI (QUIZ - ZERO API COST) */}
      {tab === "quiz" && (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="pb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <AwardIcon className="size-4 text-primary" />
                  {t("Yuridik test va davlat imtihonlari trenajyori")}
                </CardTitle>
                <p className="text-xs text-muted mt-0.5">
                  {t("Sud, advokatura va OTM imtihonlariga tayyorgarlik uchun mahalliy test savollari banki")}
                </p>
              </div>

              {/* Soha bo'yicha filter */}
              <div className="flex items-center gap-2">
                <select
                  value={quizCategory}
                  onChange={(e) => {
                    setQuizCategory(e.target.value);
                    loadQuizQuestions(e.target.value);
                  }}
                  className="rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink shadow-sm"
                >
                  <option value="ALL">{t("Barcha sohalar")}</option>
                  <option value="CIVIL">{t("Fuqarolik huquqi")}</option>
                  <option value="LABOR">{t("Mehnat huquqi")}</option>
                  <option value="CRIMINAL">{t("Jinoyat huquqi")}</option>
                  <option value="ADMINISTRATIVE">{t("Maʼmuriy huquq")}</option>
                </select>
                <Button size="sm" variant="outline" onClick={() => loadQuizQuestions(quizCategory)} disabled={quizBusy}>
                  <RefreshCwIcon className={cn("size-3.5", quizBusy && "animate-spin")} />
                </Button>
              </div>
            </CardHeader>

            <CardContent className="flex flex-col gap-6">
              {quizBusy ? (
                <div className="flex min-h-[150px] items-center justify-center">
                  <Spinner className="size-6 text-primary" />
                </div>
              ) : quizQuestions.length === 0 ? (
                <p className="text-center text-sm text-muted py-6">{t("Ushbu soha boʻyicha test savollari topilmadi")}</p>
              ) : (
                <div className="flex flex-col gap-6">
                  {quizQuestions.map((q, idx) => (
                    <div key={q.id} className="rounded-lg border border-border p-4 bg-surface">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-xs font-bold text-primary uppercase">
                          {idx + 1}-savol • {q.category_label}
                        </span>
                        {q.law_reference && (
                          <span className="text-[11px] text-muted">
                            {q.law_reference}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm font-medium text-ink leading-relaxed">
                        {q.question_text}
                      </p>

                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {q.options.map((opt) => {
                          const isSelected = userAnswers[q.id] === opt.key;
                          return (
                            <button
                              key={opt.key}
                              type="button"
                              onClick={() => setUserAnswers((prev) => ({ ...prev, [q.id]: opt.key }))}
                              className={cn(
                                "flex items-start gap-2.5 rounded-md border p-2.5 text-left text-xs transition-all",
                                isSelected
                                  ? "border-primary bg-primary/10 text-primary font-semibold"
                                  : "border-border hover:bg-subtle text-ink"
                              )}
                            >
                              <span className={cn(
                                "flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                                isSelected ? "bg-primary text-primary-foreground" : "bg-subtle text-muted"
                              )}>
                                {opt.key}
                              </span>
                              <span className="leading-snug">{opt.text}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                  <div className="flex justify-end pt-2">
                    <Button onClick={handleSubmitQuiz} disabled={quizSubmitting}>
                      {quizSubmitting ? <Spinner className="size-4" /> : <AwardIcon className="size-4" />}
                      <span>{t("Natijani tekshirish")}</span>
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Test natijalari kartasi */}
          {quizResult && (
            <Card className={cn(
              "border-2",
              quizResult.percentage >= 70 ? "border-emerald-500 bg-emerald-500/5" : "border-amber-500 bg-amber-500/5"
            )}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {quizResult.percentage >= 70 ? (
                      <CheckCircle2Icon className="size-6 text-emerald-600" />
                    ) : (
                      <XCircleIcon className="size-6 text-amber-600" />
                    )}
                    <div>
                      <CardTitle className="text-base font-semibold">
                        {quizResult.percentage >= 70 ? t("Tabriklaymiz, muvaffaqiyatli topshirdingiz!") : t("Yana ozgina tayyorgarlik talab etiladi")}
                      </CardTitle>
                      <p className="text-xs text-muted">
                        {t("Toʻgʻri javoblar:")} {quizResult.correct_count} / {quizResult.total_questions} ({quizResult.percentage.toFixed(0)}%)
                      </p>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {quizResult.details.map((d, i) => (
                  <div key={i} className="rounded-lg border border-border bg-surface p-3 text-xs">
                    <div className="flex items-start gap-2">
                      {d.is_correct ? (
                        <CheckCircle2Icon className="size-4 shrink-0 text-emerald-600 mt-0.5" />
                      ) : (
                        <XCircleIcon className="size-4 shrink-0 text-rose-600 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <p className="font-semibold text-ink">{d.question_text}</p>
                        <div className="mt-1 flex flex-wrap gap-2 text-muted">
                          <span>
                            {t("Sizning javobingiz:")} <strong>{d.selected_option}</strong>
                          </span>
                          {!d.is_correct && (
                            <span className="text-emerald-700 dark:text-emerald-400">
                              {t("Toʻgʻri javob:")} <strong>{d.correct_option}</strong>
                            </span>
                          )}
                          {d.law_reference && (
                            <span className="text-primary font-medium">
                              {t("Qonun moddasi:")} {d.law_reference}
                            </span>
                          )}
                        </div>
                        {d.explanation && (
                          <p className="mt-1.5 text-muted leading-relaxed">
                            {d.explanation}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 5. KALKULYATOR (DAVLAT BOJI VA MUDDATLAR - ZERO API COST) */}
      {tab === "calculator" && (
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <button
              type="button"
              onClick={() => setCalcTab("court_fee")}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-semibold transition-all",
                calcTab === "court_fee"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted hover:text-ink hover:bg-subtle"
              )}
            >
              {t("Davlat boji kalkulyatori (OʻRQ-600)")}
            </button>
            <button
              type="button"
              onClick={() => setCalcTab("deadline")}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-semibold transition-all",
                calcTab === "deadline"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted hover:text-ink hover:bg-subtle"
              )}
            >
              {t("Protsessual muddatlar kalkulyatori")}
            </button>
          </div>

          {calcTab === "court_fee" ? (
            <div className="grid gap-6 lg:grid-cols-12">
              <div className="flex flex-col gap-4 lg:col-span-6">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                      <CalculatorIcon className="size-4 text-primary" />
                      {t("Davlat boji parametrlari")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <div>
                      <Label className="text-xs font-semibold uppercase text-muted">
                        {t("Sud turi")}
                      </Label>
                      <div className="mt-1.5 grid grid-cols-3 gap-2">
                        {[
                          { key: "CIVIL" as const, label: t("Fuqarolik ishlari boʻyicha sud") },
                          { key: "ECONOMIC" as const, label: t("Iqtisodiy sud") },
                          { key: "ADMINISTRATIVE" as const, label: t("Maʼmuriy sud") },
                        ].map((s) => (
                          <button
                            key={s.key}
                            type="button"
                            onClick={() => setCourtType(s.key)}
                            className={cn(
                              "rounded-lg border p-2 text-xs font-medium transition-all text-center",
                              courtType === s.key
                                ? "border-primary bg-primary/10 text-primary font-semibold"
                                : "border-border hover:bg-subtle text-ink"
                            )}
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs font-semibold uppercase text-muted">
                        {t("Daʼvo turi")}
                      </Label>
                      <select
                        value={claimType}
                        onChange={(e) => setClaimType(e.target.value as any)}
                        className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-ink shadow-sm"
                      >
                        <option value="PROPERTY">{t("Mulkiy daʼvo")}</option>
                        <option value="NON_PROPERTY">{t("Nomulkiy daʼvo")}</option>
                        <option value="DIVORCE">{t("Nikohdan ajratish")}</option>
                        <option value="ORDER">{t("Sud buyrugʻi")}</option>
                        <option value="CONTRACT_DISPUTE">{t("Shartnomaviy nizo")}</option>
                      </select>
                    </div>

                    {claimType === "PROPERTY" && (
                      <div>
                        <Label htmlFor="claim-amount" className="text-xs font-semibold uppercase text-muted">
                          {t("Daʼvo bahosi (soʻmda)")}
                        </Label>
                        <Input
                          id="claim-amount"
                          type="number"
                          value={claimAmount}
                          onChange={(e) => setClaimAmount(e.target.value)}
                          placeholder="50000000"
                          className="mt-1.5 text-sm"
                        />
                      </div>
                    )}

                    {claimType === "DIVORCE" && (
                      <label className="flex items-center gap-2 text-xs text-ink cursor-pointer pt-1">
                        <input
                          type="checkbox"
                          checked={isRepeatedDivorce}
                          onChange={(e) => setIsRepeatedDivorce(e.target.checked)}
                          className="rounded border-border"
                        />
                        <span>{t("Takroriy nikohdan ajratish")} (4 BHM)</span>
                      </label>
                    )}

                    <div className="pt-2 flex justify-end">
                      <Button onClick={handleCalculateCourtFee} disabled={feeBusy}>
                        {feeBusy ? <Spinner className="size-4" /> : <CalculatorIcon className="size-4" />}
                        <span>{t("Hisoblash")}</span>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex flex-col gap-4 lg:col-span-6">
                {courtFeeResult ? (
                  <Card className="border-primary/40 bg-surface">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base font-semibold text-primary flex items-center gap-2">
                        <CheckCircle2Icon className="size-5" />
                        {t("Hisoblangan toʻlovlar")}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-lg bg-subtle p-3">
                          <span className="text-xs text-muted block">{t("Davlat boji miqdori")}</span>
                          <span className="text-lg font-bold text-ink">
                            {courtFeeResult.court_fee_uzs.toLocaleString()} {t("soʻm")}
                          </span>
                        </div>
                        <div className="rounded-lg bg-subtle p-3">
                          <span className="text-xs text-muted block">{t("Pochta xarajatlari")}</span>
                          <span className="text-lg font-bold text-ink">
                            {courtFeeResult.postal_cost_uzs.toLocaleString()} {t("soʻm")}
                          </span>
                        </div>
                      </div>

                      <div className="rounded-lg bg-primary/10 border border-primary/20 p-4">
                        <span className="text-xs font-semibold text-primary uppercase block">
                          {t("Jami toʻlov")}
                        </span>
                        <span className="text-2xl font-black text-primary">
                          {courtFeeResult.total_uzs.toLocaleString()} {t("soʻm")}
                        </span>
                      </div>

                      <div className="rounded-lg border border-border p-3 text-xs leading-relaxed text-muted">
                        <strong className="text-ink">{t("Huquqiy asosi:")}</strong> {courtFeeResult.legal_basis}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="flex min-h-[250px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center text-muted">
                    <CalculatorIcon className="size-10 text-muted/50 mb-2" />
                    <p className="text-sm font-medium">{t("Parametrlarni tanlang va hisoblash tugmasini bosing")}</p>
                    <p className="text-xs text-muted mt-1">{t("Amaldagi 1 BHM = 375 000 soʻm stavkasi boʻyicha aniq hisoblanadi")}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Protsessual muddatlar */
            <div className="grid gap-6 lg:grid-cols-12">
              <div className="flex flex-col gap-4 lg:col-span-6">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                      <CalendarIcon className="size-4 text-primary" />
                      {t("Protsessual harakat va boshlanish sanasi")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <div>
                      <Label className="text-xs font-semibold uppercase text-muted">
                        {t("Protsessual harakat")}
                      </Label>
                      <select
                        value={procedure}
                        onChange={(e) => setProcedure(e.target.value)}
                        className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-ink shadow-sm"
                      >
                        <option value="CIVIL_APPEAL">FPK: Apellatsiya shikoyati berish (1 oy)</option>
                        <option value="CIVIL_CASSATION">FPK: Kassatsiya shikoyati berish (6 oy)</option>
                        <option value="ECONOMIC_APPEAL">IPK: Apellatsiya shikoyati berish (1 oy)</option>
                        <option value="ECONOMIC_CASSATION">IPK: Kassatsiya shikoyati berish (2 oy)</option>
                        <option value="ADMIN_CLAIM">MSIYK: Hokimlik qarori ustidan sudga berish (3 oy)</option>
                        <option value="ADMIN_APPEAL">MSIYK: Sud hal qiluv qaroriga apellatsiya (1 oy)</option>
                        <option value="CRIMINAL_APPEAL">JPK: Hukm ustidan apellatsiya (20 sutka)</option>
                        <option value="CRIMINAL_CASSATION">JPK: Hukm ustidan kassatsiya (1 yil)</option>
                      </select>
                    </div>

                    <div>
                      <Label htmlFor="start-date" className="text-xs font-semibold uppercase text-muted">
                        {t("Boshlanish sanasi")} (Qaror qabul qilingan yoki topshirilgan sana)
                      </Label>
                      <Input
                        id="start-date"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="mt-1.5 text-sm"
                      />
                    </div>

                    <div className="pt-2 flex justify-end">
                      <Button onClick={handleCalculateDeadline} disabled={deadlineBusy}>
                        {deadlineBusy ? <Spinner className="size-4" /> : <CalendarIcon className="size-4" />}
                        <span>{t("Muddatni hisoblash")}</span>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex flex-col gap-4 lg:col-span-6">
                {deadlineResult ? (
                  <Card className="border-primary/40 bg-surface">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base font-semibold text-primary flex items-center gap-2">
                        <CalendarIcon className="size-5" />
                        {t("Protsessual muddat xulosasi")}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                      <div className="rounded-lg bg-primary/10 border border-primary/20 p-4">
                        <span className="text-xs font-semibold text-primary uppercase block">
                          {t("Oxirgi muddat sanasi")}
                        </span>
                        <span className="text-3xl font-black text-primary">
                          {deadlineResult.deadline_date}
                        </span>
                      </div>

                      {deadlineResult.adjusted_for_weekend && (
                        <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-xs text-amber-800 dark:text-amber-300">
                          {t("Dam olish kuniga toʻgʻri kelgani sababli keyingi ish kuniga koʻchirildi")}
                        </div>
                      )}

                      <div className="rounded-lg bg-subtle p-3 text-xs leading-relaxed text-ink">
                        <strong className="block text-muted mb-1">{t("Qoida mazmuni:")}</strong>
                        {deadlineResult.rule_description}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="flex min-h-[250px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center text-muted">
                    <CalendarIcon className="size-10 text-muted/50 mb-2" />
                    <p className="text-sm font-medium">{t("Sana va harakatni tanlang")}</p>
                    <p className="text-xs text-muted mt-1">{t("Shanba va yakshanba kunlari hisobga olingan holda oxirgi ish kuni aniqlanadi")}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 6. YURIDIK LUG'AT & RIM HUQUQI (ZERO API COST) */}
      {tab === "glossary" && (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="pb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <BookMarkedIcon className="size-4 text-primary" />
                  {t("Yuridik atamalar va Rim huquqi")}
                </CardTitle>
                <p className="text-xs text-muted mt-0.5">
                  {t("Lotincha iboralar, Rim xususiy huquqi va Oʻzbekiston qonunchiligi asosidagi atamalar glossariysi")}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={glossaryCategory}
                  onChange={(e) => {
                    setGlossaryCategory(e.target.value);
                    loadGlossary(glossaryQuery, e.target.value, onlyRomanLatin);
                  }}
                  className="rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink shadow-sm"
                >
                  <option value="ALL">{t("Barcha sohalar")}</option>
                  <option value="CIVIL">{t("Fuqarolik huquqi")}</option>
                  <option value="CRIMINAL">{t("Jinoyat huquqi")}</option>
                  <option value="LABOR">{t("Mehnat huquqi")}</option>
                  <option value="CONSTITUTIONAL">{t("Konstitutsiyaviy huquq")}</option>
                </select>

                <label className="flex items-center gap-1.5 text-xs text-ink cursor-pointer bg-subtle px-2.5 py-1 rounded-md border border-border">
                  <input
                    type="checkbox"
                    checked={onlyRomanLatin}
                    onChange={(e) => {
                      setOnlyRomanLatin(e.target.checked);
                      loadGlossary(glossaryQuery, glossaryCategory, e.target.checked);
                    }}
                    className="rounded border-border"
                  />
                  <span>{t("Faqat Rim huquqi / Lotincha aforizmlar")}</span>
                </label>
              </div>
            </CardHeader>

            <CardContent className="flex flex-col gap-4">
              <div className="relative">
                <SearchIcon className="absolute left-3 top-2.5 size-4 text-muted" />
                <Input
                  value={glossaryQuery}
                  onChange={(e) => {
                    setGlossaryQuery(e.target.value);
                    loadGlossary(e.target.value, glossaryCategory, onlyRomanLatin);
                  }}
                  placeholder={t("Atama yoki lotincha iborani qidiring...")}
                  className="pl-9 text-sm"
                />
              </div>

              {glossaryBusy ? (
                <div className="flex min-h-[150px] items-center justify-center">
                  <Spinner className="size-6 text-primary" />
                </div>
              ) : glossaryItems.length === 0 ? (
                <p className="text-center text-sm text-muted py-6">{t("Atamalar topilmadi")}</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {glossaryItems.map((item) => (
                    <div key={item.id} className="rounded-lg border border-border p-4 bg-surface flex flex-col gap-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-sm font-bold text-ink">{item.term}</span>
                          {item.latin_term && (
                            <span className="block text-xs font-serif italic text-primary">
                              {item.latin_term}
                            </span>
                          )}
                        </div>
                        <span className="rounded bg-subtle px-2 py-0.5 text-[10px] font-semibold text-primary shrink-0">
                          {item.category_label}
                        </span>
                      </div>

                      <p className="text-xs text-ink leading-relaxed">
                        {item.definition}
                      </p>

                      {item.legal_source && (
                        <div className="text-[11px] text-muted">
                          <strong>{t("Qonuniy manbasi:")}</strong> {item.legal_source}
                        </div>
                      )}

                      {item.example_usage && (
                        <div className="rounded bg-subtle/70 p-2 text-[11px] text-muted italic">
                          "{item.example_usage}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 7. SUD SIMULYATSIYASI (MOOT COURT) */}
      {tab === "moot_court" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="flex flex-col gap-4 lg:col-span-5">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <GavelIcon className="size-4 text-primary" />
                  {t("Sud majlisini simulyatsiya qilish")}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <Label htmlFor="moot-facts" className="text-xs font-semibold uppercase text-muted">
                    {t("Kazus yoki nizo holati")}
                  </Label>
                  <Textarea
                    id="moot-facts"
                    rows={5}
                    value={mootFacts}
                    onChange={(e) => setMootFacts(e.target.value)}
                    placeholder={t("Sudda koʻrilayotgan ishning toʻliq tafsilotlari va taraflar munosabatini kiriting...")}
                    className="mt-1.5 text-sm"
                  />
                </div>

                <div>
                  <Label htmlFor="moot-claim" className="text-xs font-semibold uppercase text-muted">
                    {t("Daʼvo talabi (ixtiyoriy)")}
                  </Label>
                  <Input
                    id="moot-claim"
                    value={mootClaim}
                    onChange={(e) => setMootClaim(e.target.value)}
                    placeholder={t("Masalan: Yetkazilgan 50 mln soʻm zararni undirish")}
                    className="mt-1.5 text-sm"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <Button onClick={handleSimulateMootCourt} disabled={mootBusy || !mootFacts.trim()}>
                    {mootBusy ? <Spinner className="size-4" /> : <GavelIcon className="size-4" />}
                    <span>{t("Simulyatsiyani boshlash")}</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-4 lg:col-span-7">
            {mootResult ? (
              <div className="flex flex-col gap-4">
                {/* Da'vogar */}
                <Card className="border-l-4 border-l-blue-600">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-blue-600 dark:text-blue-400">
                      {t("Daʼvogar (Ayblov / Advokat)")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2 text-xs">
                    <div>
                      <strong>{t("Pozitsiyasi va talablar:")}</strong> {mootResult.plaintiff.position}
                    </div>
                    {mootResult.plaintiff.key_arguments && mootResult.plaintiff.key_arguments.length > 0 && (
                      <div>
                        <strong>{t("Asosiy argumentlar:")}</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-0.5">
                          {mootResult.plaintiff.key_arguments.map((arg, i) => (
                            <li key={i}>{arg}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {mootResult.plaintiff.court_speech && (
                      <div className="rounded bg-blue-50 dark:bg-blue-950/40 p-2.5 italic text-blue-900 dark:text-blue-200 mt-1">
                        <strong>{t("Sud nutqi (Nutq loyihasi):")}</strong> "{mootResult.plaintiff.court_speech}"
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Javobgar */}
                <Card className="border-l-4 border-l-amber-600">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-amber-600 dark:text-amber-400">
                      {t("Javobgar (Himoya)")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2 text-xs">
                    <div>
                      <strong>{t("Pozitsiyasi va talablar:")}</strong> {mootResult.defendant.position}
                    </div>
                    {mootResult.defendant.counter_arguments && mootResult.defendant.counter_arguments.length > 0 && (
                      <div>
                        <strong>{t("Qarshi vajlar va eʼtirozlar:")}</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-0.5">
                          {mootResult.defendant.counter_arguments.map((arg, i) => (
                            <li key={i}>{arg}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {mootResult.defendant.defense_speech && (
                      <div className="rounded bg-amber-50 dark:bg-amber-950/40 p-2.5 italic text-amber-900 dark:text-amber-200 mt-1">
                        <strong>{t("Himoya nutqi loyihasi:")}</strong> "{mootResult.defendant.defense_speech}"
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Sudya */}
                <Card className="border-l-4 border-l-emerald-600">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                      {t("Sudya (Sud majlisi raisi)")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2 text-xs">
                    <div>
                      <strong>{t("Isbotlash majburiyati (Onus probandi):")}</strong> {mootResult.judge.burden_of_proof}
                    </div>
                    {mootResult.judge.decisive_questions && mootResult.judge.decisive_questions.length > 0 && (
                      <div>
                        <strong>{t("Hal qiluvchi savollar:")}</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-0.5">
                          {mootResult.judge.decisive_questions.map((q, i) => (
                            <li key={i}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div className="rounded bg-emerald-50 dark:bg-emerald-950/40 p-2.5 font-medium text-emerald-900 dark:text-emerald-200 mt-1">
                      <strong>{t("Ehtimoliy sud qarori yoʻnalishi:")}</strong> {mootResult.judge.probable_outcome}
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center text-muted">
                <GavelIcon className="size-10 text-muted/50 mb-2" />
                <p className="text-sm font-medium">{t("Ish faktlarini kiriting va sud majlisini simulyatsiya qiling")}</p>
                <p className="text-xs text-muted mt-1">{t("Daʼvogar, Javobgar va Sudya pozitsiyalari TDYU Moot Court qoidalari asosida shakllanadi")}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 8. BMI & KURS ISHI KONSTRUKTORI */}
      {tab === "thesis" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="flex flex-col gap-4 lg:col-span-5">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <GraduationCapIcon className="size-4 text-primary" />
                  {t("BMI va Kurs ishi konstruktori")}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <Label htmlFor="thesis-topic" className="text-xs font-semibold uppercase text-muted">
                    {t("Ilmiy ish mavzusi")}
                  </Label>
                  <Textarea
                    id="thesis-topic"
                    rows={3}
                    value={thesisTopic}
                    onChange={(e) => setThesisTopic(e.target.value)}
                    placeholder={t("Masalan: Oʻzbekiston Respublikasida elektron tijorat shartnomalarini huquqiy tartibga solish")}
                    className="mt-1.5 text-sm"
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold uppercase text-muted">
                    {t("Ish turi")}
                  </Label>
                  <div className="mt-1.5 flex flex-col gap-2">
                    {[
                      { key: "COURSEWORK" as const, label: t("Kurs ishi") },
                      { key: "THESIS_BACHELOR" as const, label: t("Bitiruv malakaviy ishi (BMI)") },
                      { key: "MASTER_DISSERTATION" as const, label: t("Magistrlik dissertatsiyasi") },
                    ].map((w) => (
                      <button
                        key={w.key}
                        type="button"
                        onClick={() => setThesisWorkType(w.key)}
                        className={cn(
                          "rounded-lg border p-2.5 text-xs font-medium text-left transition-all",
                          thesisWorkType === w.key
                            ? "border-primary bg-primary/10 text-primary font-semibold"
                            : "border-border hover:bg-subtle text-ink"
                        )}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button onClick={handleBuildThesisRoadmap} disabled={thesisBusy || !thesisTopic.trim()}>
                    {thesisBusy ? <Spinner className="size-4" /> : <GraduationCapIcon className="size-4" />}
                    <span>{t("Tadqiqot rejasini tuzish")}</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-4 lg:col-span-7">
            {thesisResult ? (
              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base font-bold text-ink">
                      {thesisResult.topic}
                    </CardTitle>
                    <span className="text-xs text-primary font-semibold">
                      {thesisResult.work_type_label}
                    </span>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3 text-xs leading-relaxed">
                    <div className="rounded-lg bg-subtle p-3">
                      <strong className="block text-ink mb-1">{t("Mavzuning dolzarbligi:")}</strong>
                      <p className="text-muted">{thesisResult.relevance}</p>
                    </div>

                    <div className="rounded-lg bg-subtle p-3">
                      <strong className="block text-ink mb-1">{t("Tadqiqot obyekti va predmeti:")}</strong>
                      <p className="text-muted">{thesisResult.object_and_subject}</p>
                    </div>

                    <div className="rounded-lg bg-subtle p-3">
                      <strong className="block text-ink mb-1">{t("Maqsad va vazifalar:")}</strong>
                      <p className="text-muted">{thesisResult.goal_and_tasks}</p>
                    </div>

                    <div>
                      <strong className="text-sm font-semibold text-ink block mb-2">
                        {t("Tavsiya etiladigan reja")}
                      </strong>
                      <div className="grid gap-2">
                        {thesisResult.outline?.map((sec, i) => (
                          <div key={i} className="rounded-lg border border-border p-3 bg-surface">
                            <span className="font-bold text-primary block">{sec.section}: {sec.title}</span>
                            {sec.subsections && sec.subsections.length > 0 && (
                              <ul className="list-disc pl-4 mt-1.5 space-y-1 text-muted">
                                {sec.subsections.map((sub, sIdx) => (
                                  <li key={sIdx}>{sub}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {thesisResult.regulatory_framework && thesisResult.regulatory_framework.length > 0 && (
                      <div className="rounded-lg bg-subtle p-3">
                        <strong className="block text-ink mb-1">{t("Normativ-huquqiy baza:")}</strong>
                        <ul className="list-disc pl-4 space-y-0.5 text-muted">
                          {thesisResult.regulatory_framework.map((reg, idx) => (
                            <li key={idx}>{reg}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {thesisResult.recommended_literature && thesisResult.recommended_literature.length > 0 && (
                      <div className="rounded-lg bg-subtle p-3">
                        <strong className="block text-ink mb-1">{t("Adabiyotlar roʻyxati:")}</strong>
                        <ul className="list-decimal pl-4 space-y-0.5 text-muted">
                          {thesisResult.recommended_literature.map((lit, idx) => (
                            <li key={idx}>{lit}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center text-muted">
                <GraduationCapIcon className="size-10 text-muted/50 mb-2" />
                <p className="text-sm font-medium">{t("Ilmiy ish mavzusini kiriting va reja tuzing")}</p>
                <p className="text-xs text-muted mt-1">{t("Reja TDYU va OTM talablari boʻyicha dolzarblik, obyekt, reja va adabiyotlar roʻyxatini oʻz ichiga oladi")}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
