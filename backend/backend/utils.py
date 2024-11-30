# Plot Vectorization with Crude Search Ranking Algorithm
import requests
import spacy
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob
import wikipedia
import wikipediaapi
import os 
from dotenv import load_dotenv
from pathlib import Path
import Levenshtein
import time
import pickle
from nltk.corpus import wordnet
from itertools import product

#Reduced Query Hash Approximation
from sklearn.decomposition import TruncatedSVD
from datasketch import MinHash, MinHashLSH

#vector db
from openai import OpenAI
from pinecone import Pinecone

def search_books_isbn(isbn):
    base_url = "https://www.googleapis.com/books/v1/volumes" 
    current_directory = Path.cwd()
    dotenv_path = current_directory.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path, override=True)

    params = {
        'q': f'isbn:{str(isbn)}',
        'maxResults': 1,
        'printType':'books',
        'key': os.getenv('GOOGLE_API_KEY'),
        'projection': 'full'
    }    
    response = requests.get(base_url, params=params)   
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        return data
    elif response.status_code == 403:
        print("Error 403: Forbidden. Please check your API key and its restrictions.")
        return None
    else:
        print(f"Error: Unable to fetch data (Status Code: {response.status_code})")
        return None

def POS_Extraction(text):
    '''
    Extracts adjectives, nouns, and names
    ...assuming they are most important
    '''
    nlp = spacy.load("en_core_web_md")
    doc = nlp(text)
    extraction = {"adjectives": [], "nouns": [], "names": [], "all_key_words":[]}
    lastname_distance = 0
    prev_name = ""
    for token in doc:
        if token.pos_ == "ADJ":
            extraction["adjectives"].append(token.text.lower())            
        elif token.pos_ == "NOUN":
            extraction["nouns"].append(token.text.lower())
            extraction["all_key_words"].append(token.text.lower())
            if lastname_distance == 1 and prev_name != "":
                full_name = prev_name +" "+ token.text.lower()
                extraction["names"].append(full_name)
                extraction["all_key_words"].append(full_name)
        elif token.pos_ == "PROPN":
            extraction["names"].append(token.text.lower())
            extraction["all_key_words"].append(token.text.lower())   
            
            if lastname_distance == 1:
                full_name = prev_name +" "+ token.text.lower()
                extraction["names"].append(full_name)
                extraction["all_key_words"].append(full_name)    
            lastname_distance = 0
            prev_name = token.text.lower() 
        lastname_distance +=1
    return extraction
    
def extract(text):
    '''
    chronology_info : value = (int) book number ; liklihood = (int) 1 is likely, 0 is unlikely
    genre_info : fiction = (int) 1 is fiction, 0 is nonfiction ; genres (string[]) all mentioned genres
    gender_info : (string[]) male or female. Use index to determine liklihood
    names : (string[]) all proper nouns
    '''
    POS = POS_Extraction(text)
    return POS.get("names")

def weighted_vector_embedding(text, target_words):
    # target_words = {"words":[],"word_weight_pairs":{}}
    if not len(target_words.get("words")):
        return unweighted_vector_embedding(text)
    nlp = spacy.load('en_core_web_md')
    doc = nlp(text.lower())
    embedding_dim = len(doc[0].vector)
    text_embedding = np.zeros(embedding_dim)
    total_weight = 0.0
    
    for token in doc:
        if token.text in target_words:
            weight = 1.6
        else:
            weight = 1.0
        text_embedding += weight * token.vector
        total_weight += weight

    text_embedding /= total_weight

    return text_embedding.reshape(1, -1) 

def search_books_by_query(query,top_k,key_words={}):
    query += ". "
    base_url = "https://www.googleapis.com/books/v1/volumes"    

    current_directory = Path.cwd()
    dotenv_path = current_directory.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path, override=True)
    
    params = {
        'q': query,
        'maxResults': top_k,
        'printType':'books',
        'key': os.getenv('GOOGLE_API_KEY')
    }    
    response = requests.get(base_url, params=params)    
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        return data
    elif response.status_code == 403:
        print("Error 403: Forbidden. Please check your API key and its restrictions.")
        return None
    else:
        print(f"Error: Unable to fetch data (Status Code: {response.status_code})")
        return None

def unweighted_vector_embedding(text):
    nlp = spacy.load('en_core_web_md')
    doc = nlp(text)
    return doc

def get_wiki_plot(title,search_index,reductions_applied):
    wiki = wikipediaapi.Wikipedia(user_agent="LeadTheRead/0.0 (http://leadtheread.com; leadtheread@gmail.com)")
    title = clean_title(title)
    search_results = wikipedia.search(title + "(book)")

    if len(search_results):
        if search_index > 2 or search_index > len(search_results)-1:
            return None
        title = search_results[search_index]
    else:
        # 'The Best Book' would be The at this point
        if reductions_applied > 2:
            return None
        if len(title.split(" ")) > 1:
            new_title = " ".join(title.split(" ")[: len(title.split(" ")) - 1])            
            return get_wiki_plot(new_title,search_index,reductions_applied+1)
        else:
            return None    
    page = wiki.page(title)   
    for section in page.sections:       
        section_words = [word.lower() for word in section.title.split(" ")]
        if "plot" in section_words or "summary" in section_words:
            if section.text == "":
                #Section contains sub sections
                subsections = section.sections
                for subsection in subsections:
                    if "plot" in subsection.title.lower() or "summary" in subsection.title.lower():
                        return subsection.text                
            return section.text
    # If no plot is found increase search index
    return get_wiki_plot(title,search_index+1,reductions_applied)
        
def clean_title(title):
    # Checks for title (movie) case
    if len(title.split("(")) > 1:
        return title.split("(")[0]
    return title

def openlibrary_search_isbn(isbn,top_k=1):
    '''
    isbn (string) : number identifier, it recognizes both isbn10 and isbn13
    top_k (int) : number of books to return
    '''
    query =  "isbn: " + str(isbn)
    base_url = "https://openlibrary.org/search.json"    

    params = {
        'q': query,
        'limit': top_k,
    }    
    response = requests.get(base_url, params=params)    
    if response.status_code == 200:
        simplified_resp = {"subjects":None,"key_words":None,"fiction":None,"found":False}
        data = response.json()
        if data.get("numFound") == 0:
            return simplified_resp
        else:
            simplified_resp['found'] = True
        hit = data.get("docs")[0]


def openlibrary_keys(isbn,top_k=1):
    '''
    isbn (string) : number identifier, it recognizes both isbn10 and isbn13
    top_k (int) : number of books to return
    '''
    query =  "isbn: " + isbn
    base_url = "https://openlibrary.org/search.json"    

    params = {
        'q': query,
        'limit': top_k,
    }    
    response = requests.get(base_url, params=params)    
    if response.status_code == 200:
        simplified_resp = {"subjects":[],"key_words":[],"fiction":[],"found":[]}
        data = response.json()
        if data.get("numFound") == 0:
            return simplified_resp
        else:
            simplified_resp['found'] = True
        hit = data.get("docs")[0]
        simplified_resp["fiction"] = False

        simplified_resp["subjects"] = []
        for item in hit.get('subject_key', []):
            simplified_item = item.replace("_", " ").replace("  ", " ").strip().lower()
            simplified_resp["subjects"].append(simplified_item)                

        if 'fiction' in simplified_resp.get('subjects'):
            simplified_resp["fiction"] = True
        else:
            #Checks all subjects that may contain the word fiction e.g. Young Adult Fiction
            nonfiction_list = ['nonfiction', 'non fiction', 'non-fiction']
            common_fiction_list = ['fantasy','magic','fiction']
            for genre in simplified_resp.get("subjects"):
                if genre.lower() in common_fiction_list and not genre.lower() in nonfiction_list:
                    simplified_resp["fiction"] = True
                    break

        simplified_resp["key_words"] = []
        for item in hit.get('person_key', []):
            simplified_item = item.replace("_", " ").replace("  ", " ").strip().lower()
            simplified_resp["key_words"].append(simplified_item)                
        for item in hit.get('place_key', []):
            simplified_item = item.replace("_", " ").replace("  ", " ").strip().lower()
            simplified_resp["key_words"].append(simplified_item)       

        return simplified_resp
    elif response.status_code == 403:
        print("Error 403: Forbidden. Please check your API key and its restrictions.")
        return None
    else:
        print(f"Error: Unable to fetch data (Status Code: {response.status_code})")
        return None
    
def genre_generics(genres):
    '''
    Given a list of genres, return a list of normal genres you expect to see
    genres (string[]) : list of genres
    return normalaized result
    '''
    if genres == None:
        return {"genres":[],"awards":[]}
    genre_set = {
    'action', 'adventure', 'mystery', 'thriller', 'suspense', 'fantasy', 'science', 'fiction', 
    'horror', 'romance', 'historical', 'drama', 'comedy', 'satire', 'tragedy', 'dystopian', 
    'utopian', 'apocalyptic', 'post-apocalyptic', 'crime', 'noir', 'cyber', 'steampunk','steam','punk' 
    'space', 'opera', 'western', 'epic', 'mythology', 'legend', 'fairy', 'tale', 'fable', 
    'paranormal', 'supernatural', 'gothic', 'detective', 'spy', 'espionage', 'political', 
    'legal', 'military', 'psychological', 'medical', 'speculative', 'urban', 'low', 'high', 
    'heroic', 'sword', 'sorcery', 'alternate', 'history', 'magical', 'realism', 'absurdist', 
    'existential', 'surreal', 'splatter', 'weird', 'new', 'pulp', 'hardboiled', 'cozy', 
    'whodunit', 'heist', 'courtroom', 'procedural', 'caper', 'historical', 'regency', 
    'paranormal', 'contemporary', 'new', 'erotic', 'lgbt', 
    'christian', 'religious', 'inspirational', 'mythic', 'western', 'weird',
      'poetry', 'anthology', 'young', 'adult', 'philosophical', 'metaphysical', 
    'allegory', 'tragicomedy', 'talltale', 'contemporary', 'literary', 
    'experimental', 'graphicnovel', 'visualnovel', 'epistolarynovel', 'stream', 
    'consciousness', 'psychological', 'magic', 'epic', 'sonnet', 
    'haiku', 'limerick', 'freeverse', 'ballad', 'elegy', 'ode', 'nonfiction', 'biography', 
    'autobiography', 'memoir', 'diary', 'journal', 'letters', 'essays', 'travel', 'writing', 
    'guidebook', 'selfhelp', 'instructional', 'howto', 'cookbook', 'diet', 'nutrition', 
    'health', 'fitness', 'truecrime', 'investigation', 'forensic', 'journalism', 'history', 
    'war', 'business', 'economics', 'politics', 'government', 'sociology', 'anthropology', 
    'psychology', 'philosophy', 'religion', 'theology', 'spirituality', 'newage', 'science', 
    'technology', 'nature', 'environment', 'ecology', 'astronomy', 'physics', 'chemistry', 
    'biology', 'genetics', 'medicine', 'education', 'language', 'linguistics', 'law', 
    'criminology', 'art', 'music', 'architecture', 'design', 'photography', 'film', 
    'television', 'theater', 'dance', 'media', 'rhetoric', 'literarycriticism', 
    'literarytheory', 'mythology', 'folklore', 'folktales', 'legends', 'ghoststories', 
    'classicliterature', 'epicsaga', 'series', 'chronicles', 'experimental', 
    'transgressive', 'outlaw', 'ecological', 'clifi', 'superhero', 
    'swordandsorcery', 'hardscience','hard', 'softscience','soft', 'lightnovel', 
    'serialnovel', 'picaresque','novel','literature', 'juvenile','scifi'
    }
    award_set = { 'new york', 'award', 'best seller','prize'}
    normalized_genres = {"genres":[],"awards":[]}

    for genre in genres:
        for word in genre.split(" "):
            if word in genre_set and word not in normalized_genres.get("genres"):
               normalized_genres['genres'].append(genre) 
               break
            if word in award_set and word not in normalized_genres.get("awards"):
                normalized_genres['awards'].append(genre)
                break
    return normalized_genres

#Reduced Query MinHash LSH Approximation (QRAML)

def create_minhash(shingles):
    m = MinHash(num_perm=100)
    for shingle in shingles:
        m.update(shingle.encode('utf8'))
    return m

def shingle(text, n=1):
    tokens = text.split()
    return set([" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)])

def load_minhash():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(root_dir, 'lsh_index.pkl')
    try:
        with open(file_path, 'rb') as f:
            lsh_loaded = pickle.load(f)
        return lsh_loaded
    except FileNotFoundError:
        print("Pickle file not found.")
        return None
    except Exception as e:
        print(f"Error loading MinHashLSH: {e}")
        return None

def update_minhash( key, query):
    lsh = load_minhash()
    query_shingle = shingle(query)
    query_minhash = create_minhash(query_shingle)
    lsh.insert(key, query_minhash,check_duplication=False)
    save_minhash(lsh) 

def save_minhash(lsh):
    # lsh : minhashLsh obj
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(root_dir, 'lsh_index.pkl')
    try:
        with open(file_path, 'wb') as f:
            pickle.dump(lsh, f)
        print("MinHashLSH saved successfully.")
    except Exception as e:
        print(f"Error saving MinHashLSH: {e}")

def search_minhash(query):
    lsh = load_minhash()
    query_shingle = shingle(query)
    query_minhash = create_minhash(query_shingle)
    similar_results = lsh.query(query_minhash)
    if len(similar_results) > 5:
        return similar_results[:4]
    return similar_results

def init_minhash():
    lsh = MinHashLSH(threshold=0.25, num_perm=100)
    potter_shingle = shingle("the magic boy Harry Potter and his friends go to hogwarts and fight voldemort.")
    potter_minhash = create_minhash(potter_shingle)
    lsh.insert("9780545790352",potter_minhash,check_duplication=False)
    save_minhash(lsh)

# Plot Vectorization with Crude Search Ranking Algorithm (PVCSRA)
def deep_search_books(query,vector_top_k,result_top_k,fiction):
    '''
    1. Isolate key words from query
    2. Returns a large list of books from the Google Books API matching query & key words
    3. Returns wiki plot summaries from each book
    4. Semantic search on wiki summaries to determine relavence
    5. Embeds then perform a simliarity search on the list of books and wiki summaries to the query
    3. Returns top 5 most relevant results
    '''

    # check vector db for most similar plot to query relation
    client = init_openai()
    index = init_pinecone()
    db_res = query_db(index,query,client)
    db_res.reverse()
    db_num = len(db_res) if db_res else 0

    google_books = search_books_by_query(query,15-db_num)
    google_books = google_books.get('items',[]) 
    if google_books == None:
        return [{"title": "Error Retrieving Books"}]
    
    titles = []
    for item in google_books:       
        titles.append(item.get('volumeInfo').get('title'))
        item.get("volumeInfo")["score"] = 0
    
    books = []

    similiar_query_successes = search_minhash(query)
    for isbn in similiar_query_successes:
        book = search_books_isbn(isbn)
        if book.get("totalItems") == 0:
            continue
        item = book.get("items")
        if item[0].get("volumeInfo").get("title") not in titles:
            item[0].get("volumeInfo")["score"] = 20
            google_books.append(item[0])
            titles.append(item[0].get("volumeInfo").get("title"))
        else:
            #Give big boost
            for val in google_books:
                title = val[0].get('volumeInfo', {}).get("title")
                if title == item[0].get("volumeInfo").get("title"):
                    val[0].get("volumeInfo")["score"] = 20 
    
    for book in db_res:
        if book.get("score") < .65:
            continue
        isbn = book.get("ISBN")
        title = book.get("title")
        if isbn == "None":
            full_db_res = search_books_by_query(title,1)
        else:
            full_db_res = search_books_isbn(isbn)
        if full_db_res.get("totalItems") == 0:
            if isbn != "None":
                full_db_res = search_books_by_query(title,1)
                if full_db_res.get("totalItems") == 0:
                    continue
            else:
                continue    
        #favor books found via vectordb
        full_db_res = full_db_res.get("items",None)
        if full_db_res[0].get("volumeInfo").get("title") in titles:
            for book in google_books:
                bk_title = book.get('volumeInfo', {}).get("title")
                if bk_title == full_db_res[0].get("volumeInfo").get("title"):
                    book.get("volumeInfo")["score"] = 30 
        else:
            full_db_res[0].get("volumeInfo")['score'] = 20
            google_books.append(full_db_res[0])      

    for item in google_books:       
        volume_info = item.get('volumeInfo', {})
    
        industry_identifier = volume_info.get('industryIdentifiers', 'No ISBN Listed')
        id_type = "None"
        isbn = '123456789'
        if industry_identifier == "No ISBN Listed":
            continue 
        if industry_identifier != "No ISBN Listed":
            for identifier in industry_identifier:
                if identifier.get('type') == "ISBN_13":
                    id_type = "ISBN_13"
                    isbn = identifier.get('identifier')
                    break 
                elif identifier.get('type') == "ISBN_10":
                    id_type = "ISBN_10"
                    isbn = identifier.get('identifier')
        # no isbn was listed
        if id_type == "None":
            continue
        title = volume_info.get('title', 'No title')
        #google books API for some reason reccomends these a bunch
        if title=="CannaCorn" or title == "Psychic Self-defense":
            continue
        authors_info = volume_info.get('authors', 'Unknown Author')
        authors = ""
        for author in authors_info:
            authors += author + ","
        authors = authors[:-1]
        google_description = volume_info.get('description', 'No description available')

        # Returns key words from openlibrary
        relevancy_score = volume_info.get("score")

        # Remove if internet archive goes down again soon
        key_words = openlibrary_keys(isbn)
        # if the book doesn't exist on open books punish
        # if not key_words.get("found"):
        #     relevancy_score -= 10
        #check if fiction is in key else remove book
        # if key_words.get("fiction") != fiction and key_words.get("found"):
        #     continue
        #check for matching key words such as character names
        normalized_genres = genre_generics(key_words.get("subjects"))

        # key word search in 
        key_word_copy = key_words.get("key_words").copy()
        genres_copy = normalized_genres.get("genres").copy()
        awards_copy = normalized_genres.get("awards").copy()
        for word in query:
            for key_word in key_word_copy:
                # Gets relative string difference with 1 point for every difference (capitalization, letter distance, etc.)
                distance = Levenshtein.distance(word,key_word)
                if distance == 0:
                    relevancy_score += 10
                    key_word_copy.remove(key_word)
                elif distance <= 3:
                    relevancy_score += 5
                    key_word_copy.remove(key_word)
            for key_word in genres_copy:
                distance = Levenshtein.distance(word,key_word)
                if distance == 0:
                    relevancy_score += 5
                    genres_copy.remove(key_word)
                elif distance <= 3:
                    relevancy_score += 2
                    genres_copy.remove(key_word)
            for key_word in awards_copy:
                distance = Levenshtein.distance(word,key_word)
                if distance == 0:
                    relevancy_score += 5
                    awards_copy.remove(key_word)
                elif distance <= 3:
                    relevancy_score += 2
                    awards_copy.remove(key_word)
        page_genre = ""
        genres = normalized_genres.get("genres")
        if len(genres) < 8:
            page_genre = ", ".join(genres)
        else:
            page_genre = ", ".join(genres[:7])
        for award in normalized_genres.get("awards"):
            page_genre += award + ","
        if page_genre.endswith(", "):
            page_genre = page_genre[:-1]
        page_genre = "Genres: " + page_genre
        images = volume_info.get('imageLinks', 'No image link')
        buy_link = volume_info.get("canonicalVolumeLink", "https://books.google.com/" )
        if images != 'No image link':
            image_link = images.get('smallThumbnail')
        else:
            image_link = 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/480px-No_image_available.svg.png'
        books.append({"title":title,"description": google_description,"image_link" :image_link, "isbn": isbn, "authors":authors, "buy_link":buy_link,"score":relevancy_score, "genres": page_genre})   
    # top_google = {"title" : books[0].get("title"), "description" : books[0].get("google_description"),"image_link": books[0].get("image_link"), "isbn":books[0].get("isbn"), "authors":books[0].get("authors"),"buy_link":books[0].get("buy_link"),"score":books[0].get("score"),"genres":books[0].get("genres")}
    sorted_books = sorted(books, key=lambda x: x['score'], reverse=True)
    return sorted_books[:result_top_k+1] 



def init_pinecone():
    load_dotenv()
    pinecone_key = os.getenv("PINECONE_KEY")
    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index("leadtheread")
    time.sleep(1)
    return index 

# Access Vector Database with embedded plots
def embed(text, client):
    response = client.embeddings.create(
    input=text,
    model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def query_db(index,q,client):
    query_vector = embed(q,client)
    resp = index.query(
        vector = query_vector,
        top_k = 2,
        include_metadata=True
    )
    condensed_resp = []
    for r in resp.get("matches"):
        meta = r.get("metadata")
        condensed_resp.append({"title":meta.get("title"),"ISBN":meta.get("ISBN"), "score":r.get("score")})
    return condensed_resp

def init_openai():
    load_dotenv()
    openai_key = os.getenv("OPENAI_KEY")
    client = OpenAI(api_key=openai_key)
    return client


if __name__=="__main__":
    print(deep_search_books("Magic boy goes to hogwarts",10,10,1))
    