plotsearch.com is a plot search engine with CRUD and security implementations. It's made so users can upload what they remember of a plot, and find that book title that was on the tip of their tongue. The ranking algorithm is briefly described below in the form of a diagram. The frontend is implemented with Django, the database with MySQL, and the provider is AWS. Includes email based user authentication.

Ranking Algorithm Specs:
user query -> embed to word vector -> cos similiarity in vector DB -> top 5 similarity score books ----------|
           |                                                                                                 |
           -> Shingle query -> Locality Sensitive Hashing (LSH) with Minhash -> any 90% previous matches ----|
	         |                                                                                                 |
           -> Pull keywords -> Search open library for any keyword matches -> increase book score -----------|
                                                                                                             |
                                                                                                   Results <--

