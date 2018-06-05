import znc, re, os
# this is a pile of garbage


class highlightmessages(znc.Module):
    description = "Highlights channel messages from matching nicks with specified colors, stripping out any other colors."
    module_types = [znc.CModInfo.UserModule, znc.CModInfo.NetworkModule]
    nick_limit = 100  # TODO configurable by znc admin?

    def __init__(self):
        self.defaultFGColor = 0
        self.defaultBGColor = 5
        self.bgColorFirst = False
        self.nicks = []
        self.commands = []

    def OnLoad(self, args, message):
        # the code below is in spirit of znc's AddCommand methods for CModule.
        # however, the functions fail on python lambdas.  regardless,
        # the functionality has been duplicated.  see: "AddCommand" and "AddHelpCommand" 
        # below in this module.
        def AddNick(line):
            self.OnAddNick(line)

        def RemoveNick(line):
            self.OnRemoveNick(line)

        def ListNicks(line):
            self.OnListNicks(line)

        def SetDefaultFGColor(line):
            self.OnSetDefaultFGColor(line)

        def GetDefaultFGColor(line):
            self.OnGetDefaultFGColor(line)

        def SetDefaultBGColor(line):
            self.OnSetDefaultBGColor(line)

        def GetDefaultBGColor(line):
            self.OnGetDefaultBGColor(line)

        def SetBGColorFirst(line):
            self.OnSetBGColorFirst(line)

        def GetBGColorFirst(line):
            self.OnGetBGColorFirst(line)

        self.AddHelpCommand()
        self.AddCommand("AddNick", znc.COptionalTranslation("<regex> [fg color 0-99 [bg color 0-99]]"), znc.COptionalTranslation("Add a regex pattern to match nicks for highlighting.  Optional custom highlight colors for matching nicks.  Also, it will modify existing nick highlight colors if any are or are not specified (unspecified colors revert to default).  Example: addnick user.* 1 0"), AddNick)

        self.AddCommand("RemoveNick", znc.COptionalTranslation("<regex>"), znc.COptionalTranslation("Remove a nick with a matching regular expression. Example: removenick user.*"), RemoveNick)

        self.AddCommand("ListNicks", znc.COptionalTranslation(""), znc.COptionalTranslation("List configured nicks."), ListNicks)

        self.AddCommand("SetDefaultFGColor", znc.COptionalTranslation("<0-99>"), znc.COptionalTranslation("Set default highlight color for text (foreground) from 0 - 15 (although up to 99 works on most(?) clients).  Example: setdefaultfgcolor 9"), SetDefaultFGColor)

        self.AddCommand("GetDefaultFGColor", znc.COptionalTranslation(""), znc.COptionalTranslation("Print the default FG color."), GetDefaultFGColor)

        self.AddCommand("SetDefaultBGColor", znc.COptionalTranslation("<0-99>"), znc.COptionalTranslation("Set default highlight background color from 0 - 15 (although up to 99 works on most(?) clients).  Example: setdefaultbgcolor 14"), SetDefaultBGColor)

        self.AddCommand("GetDefaultBGColor", znc.COptionalTranslation(""), znc.COptionalTranslation("Print the default BG color."), GetDefaultBGColor)

        self.AddCommand("SetBGColorFirst", znc.COptionalTranslation("<true|false>"), znc.COptionalTranslation("Swaps BG and FG color positions for some clients that read background before foreground color.  If your client is using the foreground color as the background, set this to 'true'.  Default is 'false'.  Example: setbgcolorfirst true"), SetBGColorFirst)

        self.AddCommand("GetBGColorFirst", znc.COptionalTranslation(""), znc.COptionalTranslation("Print whether or not BG colors come first."), GetBGColorFirst)


        # Load configuration files TODO maybe do configparser instead?
        self._ReadNickFile()
        self.defaultFGColor = self._ReadDefaultColorFile(self.defaultFGColor, self._GetDefaultFGFileLocation())
        self.defaultBGColor = self._ReadDefaultColorFile(self.defaultBGColor, self._GetDefaultBGFileLocation())
        self.bgColorFirst = self._CheckBGColorFirstFileExists()

        return True

    def OnChanMsg(self, nick, channel, message):
        # Check if nick matches any in the configuration, then highlight their message if a match is found.
        for nickPattern, fg, bg in self.nicks:
            if self._MatchNick(nick, nickPattern):
               # remove any colors in the original message that might impede the highlighting
               strippedMessage = re.sub('\03[0-9][0-9]?(,[0-9][0-9]?)?', '', message.s)

               # to prevent clients from assuming a number at the start of a message is actually a part of the color format, pad single digits with zeros.
               colorFormat = "\x03{0:02d},{1:02d}"

               if fg is None:
                   fg = self.defaultFGColor
               if bg is None:
                   bg = self.defaultBGColor

               highlightColor = colorFormat.format(bg, fg) if self.bgColorFirst else colorFormat.format(fg, bg)

               message.s = highlightColor + strippedMessage
               break

        return znc.CONTINUE

    def _MatchNick(self, cNick, nickPattern):
        return re.fullmatch(nickPattern, cNick.GetNickMask(), flags=re.IGNORECASE) != None

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

        fg = None
        bg = None

        if len(args) > 1:
            fg = args[1]
        if len(args) > 2:
            bg = args[2]

        bgColor = None
        fgColor = None

        if bg:
            bgColor = self._ParseColorWithMessages(bg)
            if bgColor is None:
                self.PutModule(znc.COptionalTranslation("Invalid background color. (Did you put spaces in the regex? Don't do that.)").Resolve())
                return
        if fg:
            fgColor = self._ParseColorWithMessages(fg)
            if fgColor is None:
                self.Putmodule(znc.COptionalTranslation("Invalid foreground color. (Did you put spaces in the regex? Don't do that.)").Resolve())
                return

        for i, (_nick, _fg, _bg) in enumerate(self.nicks):
            if _nick == nickPattern:
                self.nicks[i][1] = fgColor
                self.nicks[i][2] = bgColor
                self.PutModule(znc.COptionalTranslation("Modifying existing nick.").Resolve())
                self._WriteNickFile()
                return

        self.nicks.append([nickPattern, fgColor, bgColor])
        self.PutModule(znc.COptionalTranslation("Added nick.").Resolve())
        self._WriteNickFile()

    def OnRemoveNick(self, line):
        for i, (nick, fg, bg) in enumerate(self.nicks):
            if nick == line:
                self.nicks.pop(i)
                self.PutModule(znc.COptionalTranslation("Removing nick '{0}'.").Resolve().format(line))
                self._WriteNickFile()
                return

        self.PutModule(znc.COptionalTranslation("No matching nick found.").Resolve())
        return

    def _GetDefaultBGFileLocation(self):
        return os.path.join(self.GetSavePath(), "defaultbg.txt")

    def _GetDefaultFGFileLocation(self):
        return os.path.join(self.GetSavePath(), "defaultfg.txt")

    def _WriteDefaultColorFile(self, color, path):
        try:
            with open(path, "w+") as conf:
                conf.write("{:02d}".format(color))
        except IOError as e:
            print(znc.COptionalTranslation("Failed to write file '{0}': {1}").Resolve().format(path, str(e)))

    def _ReadDefaultColorFile(self, color, path):
        try:
            ret_color = color
            with open(path, "r") as conf:
                 ret_color = int(conf.readline())
            if ret_color < -1 or ret_color > 99:
                raise ValueError(znc.COptionalTranslation("Color value out of range. 0 - 99 are acceptible values").Resolve())
            return ret_color
        except (IOError, ValueError) as e:
            print(znc.COptionalTranslation("Failed to read file '{0}': {1}. Using default color '{2:02d}'.").Resolve().format(path, str(e), color))
        return color

    def _GetBGColorFirstFileLocation(self):
        return os.path.join(self.GetSavePath(), "bgcolorfirst")

    def _ModifyBGColorFirstFile(self, create):
        path = self._GetBGColorFirstFileLocation()
        try:
            if os.path.isfile(path):
                if not create:
                    os.remove(path)
            else:
                if create:
                    open(path, "w+").close()
        except (IOError, ValueError) as e:
            print(znc.COptionalTranslation("Failed to read file '{0}': {1}. Using default color '{2:02d}'.").Resolve().format(path, str(e), color))

    def _CheckBGColorFirstFileExists(self):
        return os.path.isfile(self._GetBGColorFirstFileLocation())

    def _GetNickFileLocation(self):
        return os.path.join(self.GetSavePath(), "nicks.txt")

    def _WriteNickFile(self):
        # write space separated, line separated.
        path = self._GetNickFileLocation()

        try:
            with open(path, "w+") as conf:
                for nick, fg, bg in self.nicks:
                    if fg is not None and bg is not None:
                        conf.write("{0} {1:02d} {2:02d}\n".format(nick, fg, bg))
                    elif fg is not None:
                        conf.write("{0} {1:02d}\n".format(nick, fg))
                    else:
                        conf.write("{0}\n".format(nick))
        except IOError as e:
            print(znc.COptionalTranslation("Failed to write nick file: {0}").Resolve().format(str(e)))
            return

    def _ReadNickFile(self):
        path = self._GetNickFileLocation()

        # push old nicks into something in case loading breaks
        old_nicks = self.nicks

        try:
            self.nicks = []
            with open(path, "r") as conf:
                for line in conf.read().splitlines():
                    self.OnAddNick(line)
        except IOError as e:
            print(znc.COptionalTranslation("Failed to read nick file: {0}").Resolve().format(str(e)))
            self.nicks = old_nicks
            return

    def OnListNicks(self, line):
        headers = [znc.COptionalTranslation("Nick Regex").Resolve(), znc.COptionalTranslation("FG Color").Resolve(), znc.COptionalTranslation("BG Color").Resolve()]
        rows = []

        for nick, fg, bg in self.nicks:
            rows.append([nick, "{:02d}".format(fg) if fg is not None else znc.COptionalTranslation("Default").Resolve(), "{:02d}".format(bg) if bg is not None else znc.COptionalTranslation("Default").Resolve()])

        self._WritePrettyTables(headers, rows)

    def OnSetDefaultFGColor(self, line):
        color = self._ParseColorWithMessages(line)
        if color is not None:
            self.defaultFGColor = color
            self.PutModule("DefaultFGColor = {0:02d}".format(self.defaultFGColor))
            self._WriteDefaultColorFile(color, self._GetDefaultFGFileLocation())

    def OnGetDefaultFGColor(self, line):
        self.PutModule("DefaultFGColor = {0:02d}".format(self.defaultFGColor))

    def OnSetDefaultBGColor(self, line):
        color = self._ParseColorWithMessages(line)
        if color is not None:
            self.defaultBGColor = color
            self.PutModule("DefaultBGColor = {0:02d}".format(self.defaultBGColor))
            self._WriteDefaultColorFile(color, self._GetDefaultBGFileLocation())

    def OnGetDefaultBGColor(self, line):
        self.PutModule("DefaultBGColor = {0:02d}".format(self.defaultBGColor))

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
            self._ModifyBGColorFirstFile(flag)
            return
        except ValueError:
            self.PutModule(znc.COptionalTranslation("Invalid argument.  Try 'True' or 'False'.").Resolve())
            return
        
        print(znc.COptionalTranslation("Failed to set BGColorFirst. Please consult a debugger.").Resolve())
        return

    def OnGetBGColorFirst(self, line):
        self.PutModule("BGColorFirst = {0}".format(self.bgColorFirst))

    def _ParseColorWithMessages(self, argColor):
        if not argColor.strip():
            self.PutModule(znc.COptionalTranslation("No color specified.").Resolve())
            return None

        try:
            color = int(argColor)
            if color < -1 or color > 99:
               raise ValueError

            return color
        except ValueError:
            self.PutModule(znc.COptionalTranslation("Invalid color. Please specify a number '0' through '99'.").Resolve())
            return None

        print(znc.COptionalTranslation("Failed to set color. Please consult a debugger.").Resolve())
        return None

    def OnModCommand(self, line):
        args = line.split(' ')
        if not args:
            return True

        cmd = args[0]
        line = ' '.join(args[1:])
        #print ("cmd: " + cmd + ", line:" + line)
        for cmdName, args, description, function in self.commands:
            if cmdName.lower() == cmd.lower(): # no need for case sensitivity
                function(line)
                break;

        return True

    def AddHelpCommand(self):
        def Help(line):
            self.OnHelp(line)

        self.AddCommand("Help", znc.COptionalTranslation(""), znc.COptionalTranslation("Displays this help message describing this module's commands."), Help)

    def AddCommand(self, cmdName, args, description, function):
        self.commands.append((cmdName, args, description, function))

    def OnHelp(self, line):
        headers = [znc.COptionalTranslation("Command").Resolve(), znc.COptionalTranslation("Arguments").Resolve(), znc.COptionalTranslation("Description").Resolve()]
        rows = []

        for cmdName, args, description, function in self.commands:
            rows.append([cmdName, args.Resolve(), description.Resolve()])

        self._WritePrettyTables(headers, rows)

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
