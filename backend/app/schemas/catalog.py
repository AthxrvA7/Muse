"""Spotify catalogue items, reduced to the fields Muse uses."""

from pydantic import BaseModel


class ArtistRef(BaseModel):
    id: str
    name: str


class Track(BaseModel):
    id: str
    name: str
    artists: list[ArtistRef]
    album: str
    release_year: int | None
    image_url: str | None
    spotify_url: str
    uri: str
    explicit: bool
    duration_ms: int


class Artist(BaseModel):
    id: str
    name: str
    genres: list[str]  # Spotify often returns this empty; Muse never relies on it
    image_url: str | None
    spotify_url: str
