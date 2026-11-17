"""Repositories: one per collection, the only code that reads or writes MongoDB.

Services receive a repository and call its methods; they never build queries.
Every query is built here from typed values, never from raw request JSON
(defence against NoSQL injection such as ``{"$ne": null}``).
"""
