# Public benchmark slice

This directory contains a fixed 300-question slice from the validation set of MuSiQue-Ans v1.0 and its candidate passage corpus. MuSiQue is a public multi-hop QA benchmark released under CC BY 4.0 by its authors. The upstream release contains answerable questions with two, three, or four reasoning steps; the slice has 100 questions per hop count.

`musique_v1.0_300.jsonl` stores normalized questions, gold answers, hop counts, and stable IDs for supporting paragraphs. `musique_v1.0_corpus.jsonl` stores the unique passages shown as candidates for these questions. `supporting_for` links mark which passages are gold evidence for which questions. All candidate paragraphs are included to retain the benchmark's distractors.

The sample was drawn deterministically from the official validation split with seed `20260928`, after sorting IDs within each hop group. The original full archive is not committed. To reproduce the source file and sample:

```powershell
python eval/download_public_data.py
python eval/prepare_public_sample.py data/raw/musique_ans_v1.0_dev.jsonl
```

The download script fetches the upstream release linked by the authors' repository and verifies its shape before extraction. The `manifest.json` records source checksums and the generated sample checksums. Cite the MuSiQue paper and follow its [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).

