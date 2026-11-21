"""Fon ishchi oqimi mustahkamligi: navbatdagi ish o'chirilsa/takror kelsa oqim o'lmaydi, qayta urinish atomik."""
from unittest import mock

from apps.cases import services, worker
from apps.cases.models import CaseRun

from .test_views import CaseTestBase

REPORT = {"pages": 30, "cost_usd": 0.0, "facts": [], "findings": [], "timeline": [], "summary": "ok"}


class WorkerRobustnessTests(CaseTestBase):
    def test_process_skips_deleted_or_not_queued_runs(self):
        run = self.make_run(status=CaseRun.Status.DONE)
        with mock.patch("apps.cases.pipeline.analyze_pdf") as analyze:
            worker.process(str(run.id))      # allaqachon bajarilgan — qayta ishlamaydi
            worker.process("00000000-0000-0000-0000-000000000000")   # o'chirilgan ish — xatosiz o'tadi
        analyze.assert_not_called()

    def test_loop_survives_unexpected_error(self):
        """process() kutilmagan xato ko'tarsa ham navbat oqimi o'lmaydi (keyingi ish olinadi)."""
        seen = []

        def fake_process(run_id):
            seen.append(run_id)
            if run_id == "a":
                raise RuntimeError("kutilmagan")

        worker._queue.queue.clear()
        for i, rid in enumerate(("a", "b")):
            worker._queue.put((1, i, rid))
        worker._queue.put((1, 99, "STOP"))

        def stoppable(run_id):
            if run_id == "STOP":
                raise SystemExit
            fake_process(run_id)

        with mock.patch.object(worker, "process", side_effect=stoppable):
            with self.assertRaises(SystemExit):
                worker._loop()
        self.assertEqual(seen, ["a", "b"])

    def test_report_write_failure_marks_run_failed(self):
        run = self.make_run()
        with mock.patch("apps.cases.pipeline.analyze_pdf", return_value=REPORT), \
                mock.patch("apps.cases.storage.write_encrypted", side_effect=OSError("disk to'la")):
            worker.process(str(run.id))
        run.refresh_from_db()
        self.assertEqual((run.status, run.error), (CaseRun.Status.FAILED, worker.GENERIC_ERROR))

    def test_background_error_uses_owner_language(self):
        self.user.language = "ru"
        self.user.save(update_fields=["language"])
        run = self.make_run()
        with mock.patch("apps.cases.pipeline.analyze_pdf", return_value=REPORT), \
                mock.patch("apps.cases.storage.write_encrypted", side_effect=OSError("disk to'la")):
            worker.process(str(run.id))
        run.refresh_from_db()
        self.assertEqual(run.error, "Во время анализа произошла техническая ошибка. Повторите попытку; "
                                    "если ошибка повторится, обратитесь к администратору.")

    def test_enqueue_ignores_duplicates(self):
        run = self.make_run()
        worker._queue.queue.clear()
        worker._active.discard(str(run.id))
        # setUp enqueue ni soxta bilan almashtirgan — haqiqiysini qaytaramiz (fon oqimi ishga tushmasin)
        with mock.patch.object(worker, "_thread", mock.Mock(is_alive=lambda: True)), \
                mock.patch("apps.cases.worker.enqueue", new=_REAL_ENQUEUE):
            worker.enqueue(run.id)
            worker.enqueue(run.id)
        self.assertEqual(worker._queue.qsize(), 1)
        worker._queue.queue.clear()
        worker._active.discard(str(run.id))

    def test_retry_is_atomic(self):
        run = self.make_run(status=CaseRun.Status.FAILED)
        services.retry_case(self.user, run)
        self.enqueue.assert_called_once_with(run.id)
        stale = CaseRun.objects.get(pk=run.pk)
        stale.status = CaseRun.Status.FAILED     # ikkinchi parallel so'rov eski holatni ko'radi
        with self.assertRaises(services.CaseError) as ctx:
            services.retry_case(self.user, stale)
        self.assertEqual(ctx.exception.code, "not_failed")
        self.assertEqual(self.enqueue.call_count, 1)

    def test_recover_leaves_active_runs_alone(self):
        running = self.make_run(status=CaseRun.Status.RUNNING)
        orphan = self.make_run(status=CaseRun.Status.RUNNING)
        worker._active.add(str(running.id))
        self.addCleanup(worker._active.discard, str(running.id))
        services._recovered = False
        services.recover_interrupted()
        running.refresh_from_db()
        orphan.refresh_from_db()
        self.assertEqual(running.status, CaseRun.Status.RUNNING)
        self.assertEqual(orphan.status, CaseRun.Status.FAILED)


_REAL_ENQUEUE = worker.enqueue
