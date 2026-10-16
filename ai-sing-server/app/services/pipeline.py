










































































































































        def parse_progress(line: str) -> None:
            if not line.startswith("AIS_PROGRESS="):
                return
            try:
                report_progress(int(line.removeprefix("AIS_PROGRESS=")))
            except ValueError:
                logger.warning("Ignoring invalid training progress marker: %s", line)

        report_progress(10)
        self.runner.run(
            self.settings.rvc_train_command,
            {
                "input": str(source),
                "model_dir": str(model_dir),
                "job_id": str(job_id),
            },
            parse_progress,
        )
        report_progress(35)

        model_path = model_dir / self.settings.rvc_model_filename
        index_path = model_dir / self.settings.rvc_index_filename
        if not model_path.exists():
            raise FileNotFoundError(f"RVC training finished but model file is missing: {model_path}")
        report_progress(75)
        if self.settings.rvc_index_filename and not index_path.exists():
            raise FileNotFoundError(f"RVC training finished but index file is missing: {index_path}")

        (model_dir / "manifest.txt").write_text(
            "real RVC training output\n"
            f"source={source}\n"
            f"model={model_path}\n"
            f"index={index_path}\n",
            encoding="utf-8",
        )
        report_progress(100)
        logger.info("Finished RVC training job_id=%s model=%s", job_id, model_path)
        return str(model_path)

    def run_song_processing(
        self,
        job_id: int,
        input_path: str,
        progress_callback: Callable[[int], None],
        model_path: str | None = None,
        lyrics_path: str | None = None,
    ) -> str:
        source = self._require_file(input_path, "Input file")
        logger.info("Starting song processing job_id=%s input=%s", job_id, source)
        if not self.settings.demucs_command:
            raise PipelineConfigurationError(
                "AIS_DEMUCS_COMMAND is required for real song processing. "
                "Template variables: {input}, {output_dir}, {demucs_dir}, {vocals}, {instrumental}, {job_id}."
            )
        if not self.settings.rvc_infer_command:
            raise PipelineConfigurationError(
                "AIS_RVC_INFER_COMMAND is required for real song processing. "
                "Template variables: {vocals}, {ai_vocal}, {model_path}, {output_dir}, {job_id}."
            )
        selected_model_path = model_path or self.settings.active_model_path
        if not selected_model_path:
