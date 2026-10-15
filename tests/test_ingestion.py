# tests/test_ingestion.py
import sys
import os

# Dice a Python di guardare dentro la cartella 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ingestion import run_semantic_ingestion

if __name__ == "__main__":
    print("Avvio del test di ingestione semantica...")
    
    # CORREZIONE: Puntiamo direttamente alla cartella partendo dalla root del progetto
    chunk_generati = run_semantic_ingestion(base_dir="documents_ui")
    
    print(f"\n[Test Success] La pipeline ha estratto correttamente {len(chunk_generati)} chunk dai tuoi PDF!")