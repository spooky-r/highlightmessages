# highlightmessages.py

highlightmessages.py is a ZNC module for highlighting nicks matching certain regex patterns with certain colors.

For example, you may want to 'soft ignore' somebody by setting their text color to a similar shade as the text area color, their messages aren't gone but you can read them later and you know they are speaking (and people are responding to them).
Or, possibly always know a certain person is speaking in a crowd of a hundred.

This module strips any colors inside of a message and uses the python 're' module to match nicks. The regex matches are case insensitive.
(Note: This readme is scant for now)

##### Installing ZNC:
---
- follow the guides at: https://wiki.znc.in/Installation
- when compiling, you must enable python: https://wiki.znc.in/Modpython#Compiling

##### Installing this module:
---
- put highlightmessages in ($HOME or $APPDATA$ or etc)/.znc/modules/highlightmessages.py
- load the module in znc on the web control panel OR
- load it in irc:
  + '/query &ast;status loadmod modpython'
  + '/query &ast;status loadmod highlightmessages'
  + '/query &ast;highlightmessages help' for options on configuring highlightmessages

##### Adding a nick to highlight:
---
- '/query &ast;highlightmessages addnick user.&ast;' will highlight any nick matching "user.&ast;" regex pattern (.&ast; will match anything after user) with the default configured colors.
- '/query &ast;highlightmessages addnick user.&ast; 1 12' will highlight with text color "1" and background color "12" specifically to "user.&ast;".

