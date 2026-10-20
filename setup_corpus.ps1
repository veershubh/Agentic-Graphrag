$ErrorActionPreference = "Stop"
Write-Host "Downloading arXiv papers..."
python ingest/download_arxiv_papers.py
Write-Host "Extracting papers..."
python ingest/extract_arxiv_papers.py
Write-Host "Converting papers to passages..."
python ingest/papers_to_passages.py
Write-Host "Building domain corpus inventory..."
python ingest/build_domain_corpus_inventory.py
Write-Host "Extracting domain graph..."
python graph/extract_domain_graph.py --max-passages-per-paper 1
Write-Host "Done!"
