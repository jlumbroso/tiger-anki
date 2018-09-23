# Tigerbook Anki Decks

Anki is a popular open-source spaced-repetition flashcard program, see:

- https://apps.ankiweb.net/
- https://github.com/dae/anki

This tool generates decks to help learn the names of Princeton undergraduates. It obtains its directory information (the full name) and images from the [Tigerbook API](https://github.com/alibresco/tigerbook-api).

For instance, to generate a deck for my COS 126 precept P06, I would call the program as such:
```bash
$ tiger-anki -c -o cos126_p06.apkg -t "COS126_F2018 P06" al38 blhuynh chizewer dorisli ethanl ggrajeda harir ik5 jx5 mab7 manicone mhito mmishra myzheng nhurley ryanz sprindle vtalvola zalmover
```

## Dependencies

This tool is built on top of [genanki](https://github.com/kerrickstaley/genanki), to produce Anki decks. It also uses `requests` (to interact with the Tigerbook API) and `click` (to provide a command-line interface).

## Tigerbook API configuration

This tool requires an access to the Tigerbook API, which is open to anybody who has valid Princeton credentials. You must first [retrieve your key](https://tigerbook.herokuapp.com/api/v1/getkey), and then either create a file `tigerbook_credentials.py` containing the following values:

```python
USERNAME="<Your NetID>"
API_KEY="<Your Tigerbook API key>"
```

Alternatively, you can set both as environment variables, respectively `TIGERBOOK_USR` and `TIGERBOOK_KEY`.

## History

This tool was made possible by both the original Tigerbook developed by [Hansen Qian](https://github.com/Hansenq) '16 and others, and the Tigerbook API subsequently added by [Adam Libresco](https://github.com/alibresco) '19.

In Fall 2016, it was originally implemented in JavaScript as the project "facecards" until [Dr. Christopher Moretti](https://www.cs.princeton.edu/people/profile/cmoretti) fortuitously suggested the use of Anki.