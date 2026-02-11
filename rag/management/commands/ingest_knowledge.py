"""Management command to ingest knowledge base documents into ChromaDB."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ingest knowledge base documents into ChromaDB for RAG search."

    def handle(self, *args, **options):
        try:
            from rag.ingest import ingest_all
        except ImportError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        try:
            count = ingest_all()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully ingested {count} chunks into ChromaDB.")
            )
        except ImportError as exc:
            self.stderr.write(self.style.ERROR(
                f"Missing dependency: {exc}\n"
                "Install with: pip install chromadb sentence-transformers"
            ))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Ingestion failed: {exc}"))
