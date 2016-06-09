What is this?
=============
wwwhiera is a frontend that parses the hiera data for node using
the activated classes for that node (identified through puppetdb)
and parses the hiera tree and locates all the files for that node
(will populate fact values for interpolated values)

Limitations
===========
wwwhiera...
 - must have access to the hiera data
 - currently only supports one environment
 - only supports the yaml backend for hiera
 - can not lookup fact hashes
