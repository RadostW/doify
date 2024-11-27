import re
import requests
from pybtex.database import parse_file, BibliographyData
from difflib import SequenceMatcher


def similar(a, b):
    """
    Calculate similarity between two strings using SequenceMatcher.
    """
    return SequenceMatcher(None, a, b).ratio()


def search_doi(title, author):
    """
    Query the CrossRef API for a DOI matching the given title and validate by author.
    """
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 1}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "message" in data and "items" in data["message"] and len(data["message"]["items"]) > 0:
            item = data["message"]["items"][0]
            crossref_authors = [author["family"] for author in item.get("author", []) if "family" in author]
            
            # Check if the provided author matches any CrossRef authors
            for crossref_author in crossref_authors:
                if similar(crossref_author.lower(), author.lower()) > 0.8:
                    return item.get("DOI")
    except requests.RequestException as e:
        print(f"Error querying CrossRef for title '{title}': {e}")
    return None


def process_bib_file(input_file, output_file):
    """
    Read a .bib file, look for missing DOIs, query CrossRef with title and authors, and save updated .bib file.
    """
    bib_data = parse_file(input_file)
    updated_count = 0

    for entry_key, entry in bib_data.entries.items():
        # Check if DOI is missing
        if "doi" not in entry.fields:
            title = entry.fields.get("title", "")
            authors = entry.persons.get("author", [])
            if title and authors:
                # Get the first author for comparison
                first_author = str(authors[0].last_names[0])
                print(f"Searching DOI for title: '{title}' by {first_author}")
                doi = search_doi(title, first_author)
                if doi:
                    entry.fields["doi"] = doi
                    updated_count += 1
                    print(f"DOI found: {doi}")
                else:
                    print("DOI not found or authors didn't match.")
            else:
                print(f"No title or authors found for entry '{entry_key}', skipping DOI search.")

    # Write the updated .bib file
    with open(output_file, "w") as out_file:
        bib_data.to_file(out_file, bib_format="bibtex")

    print(f"Processed {len(bib_data.entries)} entries. Updated {updated_count} with DOIs.")
    print(f"Updated .bib file written to '{output_file}'.")


# Main script execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update a .bib file with missing DOIs using CrossRef.")
    parser.add_argument("input_file", help="Input .bib file")
    parser.add_argument("output_file", help="Output .bib file with updated DOIs")
    args = parser.parse_args()

    process_bib_file(args.input_file, args.output_file)

