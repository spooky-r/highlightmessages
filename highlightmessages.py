import znc, re, os


class highlightmessages(znc.Module):
    description = "Highlights channel messages from matching nicks with specified colors, stripping out any other colors."
    module_types = [znc.CModInfo.UserModule, znc.CModInfo.NetworkModule]
    nick_limit = 100  # TODO configurable by znc admin?
    
    @property
    def bgColorFirst(self):
        return self._bgColorFirst

    @bgColorFirst.setter
    def bgColorFirst(self, value):
        if value.lower() == "true":
            self._bgColorFirst = True
        elif value.lower() == "false":
            self._bgColorFirst = False
        else:
            raise ValueError(znc.COptionalTranslation("Invalid value '{0}'.  Acceptible values: 'true', 'false'.").Resolve().format(value))

    @property
    def defaultBGColor(self):
        return self._defaultBGColor

    @defaultBGColor.setter
    def defaultBGColor(self, value):
        self._defaultBGColor = self._CheckColorValue(value)

    @property
    def defaultFGColor(self):
        return self._defaultFGColor

    @defaultFGColor.setter
    def defaultFGColor(self, value):
        self._defaultFGColor = self._CheckColorValue(value)

    def __init__(self):
        self._defaultFGColor = 0
        self._defaultBGColor = 5
        self._bgColorFirst = False
        self.nicks = []
        self.commands = []
        self.config = znc.CConfig()

    ## ===== znc.CModule methods =====
    def AddCommand(self, cmdName, args, description, function):
        self.commands.append((cmdName, args, description, function))

    def AddHelpCommand(self):
        def Help(line):
            self.OnHelp(line)

        self.AddCommand("Help", znc.COptionalTranslation(""), znc.COptionalTranslation("Displays this help message describing this module's commands."), Help)

    def OnChanActionMessage(self, message):
        self._ParseMessage(message)
        return znc.CONTINUE

    def OnChanTextMessage(self, message):
        self._ParseMessage(message)
        return znc.CONTINUE

    def OnLoad(self, args, message):
        # the code below is in spirit of znc's AddCommand methods for CModule.
        # however, the functions fail on python lambdas.  regardless,
        # the functionality has been duplicated.  see: "AddCommand" and "AddHelpCommand" 
        # below in this module.
        def AddNick(line):
            self.OnAddNick(line)
        def GetBGColorFirst(line):
            self.OnGetBGColorFirst(line)
        def GetDefaultBGColor(line):
            self.OnGetDefaultBGColor(line)
        def GetDefaultFGColor(line):
            self.OnGetDefaultFGColor(line)
        def ListNicks(line):
            self.OnListNicks(line)
        def LoadConfig(line):
            self.OnLoadConfig(line)
        def RemoveNick(line):
            self.OnRemoveNick(line)
        def SaveConfig(line):
            self.OnSaveConfig(line)
        def SetBGColorFirst(line):
            self.OnSetBGColorFirst(line)
        def SetDefaultBGColor(line):
            self.OnSetDefaultBGColor(line)
        def SetDefaultFGColor(line):
            self.OnSetDefaultFGColor(line)

        self.AddHelpCommand()
        self.AddCommand("AddNick", znc.COptionalTranslation("<regex> [fg color 0-99 [bg color 0-99]]"), znc.COptionalTranslation("Add a regex pattern to match nicks for highlighting with optional custom highlight colors for the nick.  If the nick exists, modify the nick's colors where unspecified colors revert to default.  Example: addnick user.* 1 0"), AddNick)
        self.AddCommand("GetBGColorFirst", znc.COptionalTranslation(""), znc.COptionalTranslation("Print whether or not BG colors come first."), GetBGColorFirst)
        self.AddCommand("GetDefaultBGColor", znc.COptionalTranslation(""), znc.COptionalTranslation("Print the default BG color."), GetDefaultBGColor)
        self.AddCommand("GetDefaultFGColor", znc.COptionalTranslation(""), znc.COptionalTranslation("Print the default FG color."), GetDefaultFGColor)
        self.AddCommand("ListNicks", znc.COptionalTranslation(""), znc.COptionalTranslation("List configured nicks."), ListNicks)
        self.AddCommand("LoadConfig", znc.COptionalTranslation(""), znc.COptionalTranslation("Load the configuration file for this module, if it exists.", LoadConfig)
        self.AddCommand("RemoveNick", znc.COptionalTranslation("<regex>"), znc.COptionalTranslation("Remove a nick with a matching regular expression. Example: removenick user.*"), RemoveNick)
        self.AddCommand("SaveConfig", znc.COptionalTranslation(""), znc.COptionalTranslation("Save the current configuration of this module to disk."), SaveConfig)
        self.AddCommand("SetBGColorFirst", znc.COptionalTranslation("<true|false>"), znc.COptionalTranslation("Swaps BG and FG color positions for some clients that read background before foreground color.  If your client is using the foreground color as the background, set this to 'true'.  Default is 'false'.  Example: setbgcolorfirst true"), SetBGColorFirst)
        self.AddCommand("SetDefaultBGColor", znc.COptionalTranslation("<0-99>"), znc.COptionalTranslation("Set default highlight background color from 0 - 15 (although up to 99 works on most(?) clients).  Example: setdefaultbgcolor 14"), SetDefaultBGColor)
        self.AddCommand("SetDefaultFGColor", znc.COptionalTranslation("<0-99>"), znc.COptionalTranslation("Set default highlight color for text (foreground) from 0 - 15 (although up to 99 works on most(?) clients).  Example: setdefaultfgcolor 9"), SetDefaultFGColor)

        self.OnLoadConfig("")

        return True

    def OnModCommand(self, line):
        # attempting to keep in the spirit of AddCommand, i had to write this
        # note to self: fix modpython so AddCommand works and this function unnecessary?
        args = line.split(' ', 1)
        if not args:
            return True

        cmd = args[0]
        line = args[1]
        for cmdName, args, description, function in self.commands:
            if cmdName.lower() == cmd.lower(): # no need for case sensitivity
                function(line)
                break

        return True

    ## ====== Module commands =====
    def OnAddNick(self, line):
        if len(self.nicks) >= self.nick_limit:
            self.PutModule(znc.COptionalTranslation("Reached nick limit of {0}, cannot add any more.").Resolve().format(nick_limit))
            return

        args = line.split(' ')
        if not args or len(args) <= 0:
            self.PutModule(znc.COptionalTranslation("No args provided.").Resolve())
            return

        nickPattern = args[0]
        if not nickPattern.strip() or nickPattern == "":
          self.PutModule(znc.COptionalTranslation("No nick regex found.").Resolve())
          return

        bgColor = None
        fgColor = None

        if len(args) > 1:
            try:
                fgColor = self._CheckColorValue(args[1])
            except ValueError as e:
                self.Putmodule(znc.COptionalTranslation("Invalid fg color '{0}'. {1}.").Resolve().format(args[1], str(e)))
                return

        if len(args) > 2:
            try:
                bgColor = self._CheckColorValue(args[2])
            except ValueError as e:
                self.Putmodule(znc.COptionalTranslation("Invalid bg color '{0}'. {1}.").Resolve().format(args[2], str(e)))
                return

        for i, (_nick, _fg, _bg) in enumerate(self.nicks):
            if _nick == nickPattern:
                self.nicks[i][1] = fgColor
                self.nicks[i][2] = bgColor
                self.PutModule(znc.COptionalTranslation("Modifying existing nick.").Resolve())
                return

        self.nicks.append([nickPattern, fgColor, bgColor])
        self.PutModule(znc.COptionalTranslation("Added nick.").Resolve())

    def OnGetBGColorFirst(self, line):
        self.PutModule("BGColorFirst = {0}".format(self.bgColorFirst))

    def OnGetDefaultBGColor(self, line):
        self.PutModule("DefaultBGColor = {0:02d}".format(self.defaultBGColor))

    def OnGetDefaultFGColor(self, line):
        self.PutModule("DefaultFGColor = {0:02d}".format(self.defaultFGColor))

    def OnHelp(self, line):
        headers = [znc.COptionalTranslation("Command").Resolve(), znc.COptionalTranslation("Arguments").Resolve(), znc.COptionalTranslation("Description").Resolve()]
        rows = []

        for cmdName, args, description, function in self.commands:
            rows.append([cmdName, args.Resolve(), description.Resolve()])

        self._WritePrettyTables(headers, rows)

    def OnListNicks(self, line):
        headers = [znc.COptionalTranslation("Nick Regex").Resolve(), znc.COptionalTranslation("FG Color").Resolve(), znc.COptionalTranslation("BG Color").Resolve()]
        rows = []

        for nick, fg, bg in self.nicks:
            rows.append([nick, "{:02d}".format(fg) if fg is not None else znc.COptionalTranslation("Default").Resolve(), "{:02d}".format(bg) if bg is not None else znc.COptionalTranslation("Default").Resolve()])

        self._WritePrettyTables(headers, rows)

    def OnLoadConfig(self, line):
        pass

    def OnRemoveNick(self, line):
        for i, (nick, fg, bg) in enumerate(self.nicks):
            if nick == line:
                self.nicks.pop(i)
                self.PutModule(znc.COptionalTranslation("Removing nick '{0}'.").Resolve().format(line))
                return

        self.PutModule(znc.COptionalTranslation("No matching nick found.").Resolve())
        return

    def OnSaveConfig(self, line):
        pass

    def OnSetBGColorFirst(self, line):
        try:
            flag = None
            if line.lower() == 'true':
                flag = True
            elif line.lower() == 'false':
                flag = False
            else:
                raise ValueError(znc.COptionalTranslation("Unrecognized string value '{0}'.  'true' or 'false' case insensitive are the only two acceptible values.").Resolve().format(line))

            self.bgColorFirst = flag
            self.PutModule("SetBGColorFirst = {0}".format(flag))
            return
        except ValueError:
            self.PutModule(znc.COptionalTranslation("Invalid argument.  Try 'True' or 'False'.").Resolve())
            return
        
        print(znc.COptionalTranslation("Failed to set BGColorFirst. Please consult a debugger.").Resolve())
        return

    def OnSetDefaultBGColor(self, line):
        try
            self.defaultBGColor = line
            self.PutModule("DefaultBGColor = {0:02d}".format(self.defaultBGColor))

    def OnSetDefaultFGColor(self, line):
        try
            self.defaultFGColor = line
            self.PutModule("DefaultFGColor = {0:02d}".format(self.defaultFGColor))
        except ValueError as e:
            self.PutModule(znc.COptionalTranslation(
            
    ## ===== Utility methods =====
    def _CheckColorValue(self, value):
        color = int(value)
        if value < 0 or value > 99:
            raise ValueError(znc.COptionalTranslation("Value '{0}' is out of range.  Acceptible values are 0 - 99.").Resolve().format(value))
        return color

    def _GetConfigFileLocation(self):
        return os.path.join(self.GetSavePath(), "highlightmessage.conf")

    def _ParseMessage(self, message):
        # Check if nick matches any in the configuration, then highlight their message if a match is found.
        for nickPattern, fg, bg in self.nicks:
            if re.fullmatch(nickPattern, message.GetNick().GetNickMask(), flags=re.IGNORECASE) != None:
                # remove any colors in the original message that might impede the highlighting
                strippedMessage = re.sub('\03[0-9][0-9]?(,[0-9][0-9]?)?', '', message.GetText())

                # to prevent clients from assuming a number at the start of a message is actually a part of the color format, pad single digits with zeros.
               colorFormat = "\x03{0:02d},{1:02d}"

                if fg is None:
                   fg = self.defaultFGColor
                if bg is None:
                   bg = self.defaultBGColor

                highlightColor = colorFormat.format(bg, fg) if self.bgColorFirst else colorFormat.format(fg, bg)

                message.s = highlightColor + strippedMessage
                break
           

    def _WritePrettyTables(self, headers, rows):
        # find out the longest width required to fit data in a column
        longestWidth = []
        columnCount = len(headers)
        for header in headers:
            longestWidth.append(len(header))

        for row in rows:
            for i, column in enumerate(row):
                if longestWidth[i] < len(column):
                    longestWidth[i] = len(column)

        # draw each column of data to each row.
        lines = [""] * (len(rows) + 4) # + 3 for header, + 1 for footer
        for i in range(columnCount):
            # header
            lines[0] += "+" + ("=" * (longestWidth[i] + 2)) # + 2 for spaces on line below
            _str = "| {:" + str(longestWidth[i]) + "} "
            lines[1] += _str.format(headers[i])
            lines[2] += "+" + ("=" * (longestWidth[i] + 2))

            # rows
            for x in range(len(rows)):
                _str =  "| {:" + str(longestWidth[i]) + "} "
                lines[x + 3] += _str.format(rows[x][i])

            # footer
            lines[-1] += "+" + ("-" * (longestWidth[i] + 2))

        # cap the ends
        lines[0] += "+"
        lines[1] += "|"
        lines[2] += "+"
        for x in range(len(rows)):
            lines[x + 3] += "|"
        lines[-1] += "+"

        for line in lines:
            self.PutModule(line)

        return

