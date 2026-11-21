/**
 * Ish PDF ini ko'rsatish (pdf.js). Fayl token bilan yuklanadi (iframe emas — Authorization sarlavhasi kerak),
 * faqat xotirada turadi, keshlanmaydi. `page` tashqaridan boshqariladi: hisobotdagi varaq tugmalari shu yerga o'tkazadi.
 */
import { ChevronLeftIcon, ChevronRightIcon, ZoomInIcon, ZoomOutIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/TextLayer.css";
import { api, Spinner } from "@mezon/web-kit";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

export function PdfViewer({ caseId, page, onPageChange }: { caseId: string; page: number; onPageChange(n: number): void }) {
  const { t } = useTranslation();
  const [data, setData] = useState<Uint8Array | null>(null);
  const [error, setError] = useState("");
  const [numPages, setNumPages] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(600);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError("");
    api
      .raw(`/cases/${caseId}/pdf`, { cache: "no-store" })
      .then((r) => r.arrayBuffer())
      .then((buf) => alive && setData(new Uint8Array(buf)))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [caseId]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width - 24)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // react-pdf faylni obyekt identifikatori bo'yicha qayta yuklaydi — memo shart
  const file = useMemo(() => (data ? { data: data.slice() } : null), [data]);
  const go = (n: number) => onPageChange(Math.min(Math.max(1, n), numPages || 1));

  return (
    <div className="flex h-full min-h-0 flex-col bg-subtle">
      <div className="flex items-center gap-1 border-b border-line bg-surface px-2 py-1.5">
        <button className="rounded p-1.5 text-muted hover:bg-subtle hover:text-ink disabled:opacity-40" onClick={() => go(page - 1)} disabled={page <= 1} aria-label="←">
          <ChevronLeftIcon className="size-4" />
        </button>
        <input
          type="number" min={1} max={numPages || 1} value={page} onChange={(e) => go(Number(e.target.value))}
          className="h-8 w-14 rounded-md border border-line bg-surface text-center tabular-nums text-sm outline-none focus:border-primary"
          aria-label={t("Varaq")}
        />
        <span className="tabular-nums text-xs text-muted">/ {numPages || "…"}</span>
        <button className="rounded p-1.5 text-muted hover:bg-subtle hover:text-ink disabled:opacity-40" onClick={() => go(page + 1)} disabled={page >= numPages} aria-label="→">
          <ChevronRightIcon className="size-4" />
        </button>
        <div className="ml-auto flex items-center gap-1">
          <button className="rounded p-1.5 text-muted hover:bg-subtle hover:text-ink" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} aria-label="−">
            <ZoomOutIcon className="size-4" />
          </button>
          <span className="w-10 text-center tabular-nums text-xs text-muted">{Math.round(zoom * 100)}%</span>
          <button className="rounded p-1.5 text-muted hover:bg-subtle hover:text-ink" onClick={() => setZoom((z) => Math.min(3, z + 0.25))} aria-label="+">
            <ZoomInIcon className="size-4" />
          </button>
        </div>
      </div>
      <div ref={boxRef} className="min-h-0 flex-1 overflow-auto p-3">
        {error ? (
          <div className="p-6 text-sm text-muted">{error}</div>
        ) : !file ? (
          <div className="grid h-full place-items-center"><Spinner className="size-6" /></div>
        ) : (
          <Document file={file} onLoadSuccess={(pdf) => setNumPages(pdf.numPages)} loading={<Spinner className="mx-auto mt-10 size-6" />}
            error={<div className="p-6 text-sm text-red">{t("PDF oʻchirilgan yoki topilmadi")}</div>}>
            <Page pageNumber={Math.min(page, numPages || 1)} width={width * zoom} renderAnnotationLayer={false}
              className="mx-auto w-fit shadow-overlay" loading={<Spinner className="mx-auto mt-10 size-6" />} />
          </Document>
        )}
      </div>
    </div>
  );
}
