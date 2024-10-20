Leadtheread is my attempt to solve the issue of forgetting the title of a book you read in the past.
https://leadtheread.com

Technical Aspects:
Built a ranking algorithm utilizing NLP to calculate vector similarity scores between user queries and Wikipedia plots then further improved accuracy by 25% via checking for the presence of keywords, genres, and awards using Open Library data.
Utilized Locality sensitive hashing to store and search successful query to liked book instances via MinHash for continual ranking algorithm improvement and abundance.
Deployed the site on AWS, integrated with a MySQL database, and implemented the backend using Javascript and Django, featuring CSRF protection, email authentication, and email based password reset functionalities.

Current Issues:
As Internet Archive is down, search accuracy is also decreased as leadtheread uses the Open Library API
