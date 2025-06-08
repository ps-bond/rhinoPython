# Ring Size Generator

Script to install a custom command for a ring size generator in Rhino 8


Adds a class and an alias to Rhino that will allow generation of circles on the current construction plane.  Uses a dataset from the wiki page https://en.wikipedia.org/wiki/Ring_size to generate the sizes for all the country sizing systems listed there.


There's a utility to generate the ring sizes data by scraping the wiki page; this is more for my benefit as the resulting data is stored in ring_sizes.py

Run the script with 

`RunPythonScript` 

Find the file `ringSizeGenerator.py` and select it.  `ring_size.py` needs to be in the same directory (or pathed to it).

The alias to reshow the window is
`ShowRingsizeGenerator`

## To do

Localisation?  Could be interesting to do.

