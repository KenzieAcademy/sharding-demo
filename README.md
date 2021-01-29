# An Intro to Database Sharding

The `controller.py` file in this repository takes the file named `text.txt` and emulates a simple horizontally sharded database, allowing easy understanding of how data is distributed across nodes. This particular handler is unfinished; it can initialize nodes and add nodes to an initialized list, but it cannot remove nodes or handle replication. That is an exercise for the reader.

Content in `text.txt` retrieved from <http://www.gutenberg.org/files/11/11-h/11-h.htm>

To reset everything for a fresh run, just execute `make clean` in your terminal.
