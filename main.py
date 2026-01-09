import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from tkinter import Tk, filedialog


class TCReviewer:
    def __init__(self, db_file='tc_reviews.json'):
        self.db_file = db_file
        self.reviewed_sections = self.load_database()

    def load_database(self) -> Dict:
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_database(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.reviewed_sections, f, indent=2, ensure_ascii=False)

    def hash_section(self, text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def split_into_sections(self, text: str) -> List[str]:
        sections = []
        import re
        patterns = [
            # Standalone section headers (lines that are mostly caps and short)
            r'\n(?=[A-Z][A-Z\s&\'-]{5,80}\n)',
            # Numbered sections like "1. ", "2. "
            r'\n(?=\d+\.\s)',
            # Article format
            r'\n(?=Article\s+\d+)',
            # Section format
            r'\n(?=Section\s+\d+)',
        ]

        for pattern in patterns:
            potential_sections = re.split(pattern, text)
            if len(potential_sections) > 5:  # Must create at least 5 sections to be useful
                sections = [s.strip() for s in potential_sections if s.strip()]
                break
        if len(sections) < 5:
            sections = [s.strip() for s in text.split('\n\n') if s.strip() and len(s.strip()) > 100]
        if len(sections) < 5:
            sections = [s.strip() for s in text.split('\n') if len(s.strip()) > 200]
        if len(sections) < 5:
            sections = self.chunk_by_size(text, min_chars=300, max_chars=2000)
        return sections

    def chunk_by_size(self, text: str, min_chars: int = 300, max_chars: int = 2000) -> List[str]:
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > max_chars and current_length >= min_chars:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1
        if current_chunk and current_length >= min_chars:
            chunks.append(' '.join(current_chunk))
        elif current_chunk and chunks:
            chunks[-1] += ' ' + ' '.join(current_chunk)
        return chunks if chunks else [text]

    def select_file(self) -> str:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        filepath = filedialog.askopenfilename(
            title="Select T&C Text File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        root.destroy()
        return filepath

    def load_tc_file(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def wrap_text(self, text: str, width: int = 80) -> str:
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        for word in words:
            word_length = len(word)
            space_needed = word_length + (1 if current_line else 0)
            if current_length + space_needed <= width:
                current_line.append(word)
                current_length += space_needed
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        if current_line:
            lines.append(' '.join(current_line))
        return '\n'.join(lines)

    def review_section(self, section: str, section_hash: str) -> str:
        print("\n" + "=" * 80)
        print("SECTION TO REVIEW:")
        print("=" * 80)
        wrapped_section = self.wrap_text(section, 80)
        print(wrapped_section)
        print("=" * 80)
        while True:
            choice = input("\nApprove (a), Disapprove (d), or Skip (s)? ").lower()
            if choice in ['a', 'd', 's']:
                if choice == 'a':
                    return 'approved'
                elif choice == 'd':
                    return 'disapproved'
                else:
                    return 'skipped'
            print("Invalid choice. Please enter 'a', 'd', or 's'.")

    def process_tc_file(self, filepath: str):
        print(f"\nProcessing: {filepath}")
        text = self.load_tc_file(filepath)
        sections = self.split_into_sections(text)
        print(f"Found {len(sections)} sections")
        new_sections = 0
        approved = 0
        disapproved = 0
        skipped = 0
        already_reviewed = 0
        for i, section in enumerate(sections, 1):
            section_hash = self.hash_section(section)
            if section_hash in self.reviewed_sections:
                status = self.reviewed_sections[section_hash]['status']
                already_reviewed += 1
                print(f"\n[{i}/{len(sections)}] Already reviewed: {status}")
            else:
                new_sections += 1
                print(f"\n[{i}/{len(sections)}] NEW SECTION")
                status = self.review_section(section, section_hash)
                if status != 'skipped':
                    self.reviewed_sections[section_hash] = {
                        'status': status,
                        'preview': section[:200]}
                    self.save_database()
                if status == 'approved':
                    approved += 1
                elif status == 'disapproved':
                    disapproved += 1
                else:
                    skipped += 1
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total sections: {len(sections)}")
        print(f"Already reviewed: {already_reviewed}")
        print(f"New sections: {new_sections}")
        print(f"Approved: {approved}")
        print(f"Disapproved: {disapproved}")
        print(f"Skipped: {skipped}")
        print("=" * 80)
        self.provide_verdict(sections, skipped)

    def provide_verdict(self, sections: List[str], skipped_count: int):
        all_sections_reviewed = True
        has_disapproved = False
        has_approved = False
        for section in sections:
            section_hash = self.hash_section(section)
            if section_hash in self.reviewed_sections:
                status = self.reviewed_sections[section_hash]['status']
                if status == 'disapproved':
                    has_disapproved = True
                elif status == 'approved':
                    has_approved = True
            else:
                all_sections_reviewed = False
        if skipped_count > 0:
            all_sections_reviewed = False
        print("\n" + "=" * 80)
        print("FINAL VERDICT")
        print("=" * 80)
        if not all_sections_reviewed:
            print("INCOMPLETE REVIEW")
            print("Some sections have not been reviewed yet.")
        elif has_disapproved:
            print("THIS T&C CONTAINS DISAPPROVED SECTIONS")
            print("This document has one or more sections that were disapproved.")
        elif has_approved and not has_disapproved:
            print("THIS T&C HAS ALL APPROVED SECTIONS")
            print("All sections in this document have been approved.")
        else:
            print("NO SECTIONS REVIEWED")
        print("=" * 80)

    def view_database(self):
        if not self.reviewed_sections:
            print("No sections reviewed yet.")
            return
        approved = sum(1 for v in self.reviewed_sections.values() if v['status'] == 'approved')
        disapproved = sum(1 for v in self.reviewed_sections.values() if v['status'] == 'disapproved')
        print(f"\nTotal reviewed sections: {len(self.reviewed_sections)}")
        print(f"Approved: {approved}")
        print(f"Disapproved: {disapproved}")
        if input("\nShow all sections? (y/n): ").lower() == 'y':
            for hash_val, data in self.reviewed_sections.items():
                print(f"\n{data['status'].upper()}: {data['preview']}")

    def clear_database(self):
        confirm = input("Are you sure you want to clear all reviews? (yes/no): ")
        if confirm.lower() == 'yes':
            self.reviewed_sections = {}
            self.save_database()
            print("Database cleared.")
        else:
            print("Cancelled.")


def main():
    reviewer = TCReviewer()
    print("=" * 80)
    print("TERMS & CONDITIONS REVIEW SYSTEM")
    print("=" * 80)
    while True:
        print("\nOptions:")
        print("1. Review a T&C file")
        print("2. View review database")
        print("3. Clear database")
        print("4. Exit")
        choice = input("\nEnter choice (1-4): ").strip()
        if choice == '1':
            filepath = reviewer.select_file()
            if filepath:
                reviewer.process_tc_file(filepath)
            else:
                print("No file selected.")
        elif choice == '2':
            reviewer.view_database()
        elif choice == '3':
            reviewer.clear_database()
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()