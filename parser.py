import os
import time
import regex as re

from character_fetcher import Cache

TESTING = False

TIMESTAMP_REGEX = "\\[ 20[0-9][0-9].[0-9][0-9].[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9] \\]"

YOU_STRING = "[PLAYER]"
"""
TODOs:
* Unify target names: Make sure we know who it is, corp, and alliance ticker if possible
* Find Target Images (and cache!)
* UI
"""

def is_log_line(line):
    return re.match(f"{TIMESTAMP_REGEX} .*", line)


# def is_damage_line(line):


class Line:
    def __init__(self, text, parsed=False):
        self.parsed = parsed
        self.text = text.strip()

    def __str__(self):
        return self.text

    @staticmethod
    def parse(text):
        type = re.match(f"{TIMESTAMP_REGEX} \\(([^)]*)\\) .*", text).group(1)
        if type == "combat":
            combat_damage_matches = re.match(
                f"{TIMESTAMP_REGEX}.*<color=0x[0-9a-fA-F]*><font size=[0-9]*>([^<]*)</font> <b><color=0x[0-9a-fA-F]*>([^[>]*)(\\[[^]]*\\])*\\(([^)]*)\\)</b><font size=[0-9]*><color=0x[0-9a-fA-F]*> - (.*) - (.*)$",
                text)
            if combat_damage_matches:
                print(combat_damage_matches.groups())
                outgoing, target, _ticker, ship, module, hit_type = combat_damage_matches.groups()
                return DamageCombatLine(text, outgoing == "to", target, ship, module, hit_type)
            miss_you_matches = re.match(f"{TIMESTAMP_REGEX}.*\\(combat\\).*?(belonging to (.*) )*misses you completely - (.*)", text)
            if miss_you_matches:
                _, possible_source_player, weapon_type = miss_you_matches.groups()
                return MissCombatLine(text, YOU_STRING, possible_source_player, weapon_type)
            miss_target_matches = re.match(f"{TIMESTAMP_REGEX}.*Your.*misses (.*) completely - (.*)$", text)
            if miss_target_matches:
                target, weapon_type = miss_target_matches.groups()
                return MissCombatLine(text, target, YOU_STRING, weapon_type)
            warp_block_combat_matches = re.match(
                rf"{TIMESTAMP_REGEX}.*<b>(Warp [^<]*)</b>.*<font size=[0-9]*>([^<]*).*<b>(([^<[]*) (\[[^]*]*\])*\((.*)\)|you)</b>.*<font size=[0-9]*>([^ ]*) <b>.*</font>([^[]*?)( \[[^]]*\])*(\([^)]*\))?$",
                text)
            if warp_block_combat_matches:
                disrupt_type, _, source, name, source_ship, _, _, target, _, target_ship = warp_block_combat_matches.groups()
                if name is not None:
                    source = name
                if target_ship and target_ship.startswith("("):
                    target_ship = target_ship[1:-1]
                elif not target_ship:
                    target_ship = "NPC"
                if target == "you!":
                    target = YOU_STRING
                if source == "you":
                    source = YOU_STRING
                return WarpBlockCombatLine(text, disrupt_type, _, source.strip(), _, target.strip(), target_ship, source_ship)
            warp_block_combat_alt_matches = re.match(f"{TIMESTAMP_REGEX}.*(Warp [^<]*)</b>.*>(from|to)<.*>you<.*>to <b><color=0x[0-9a-fA-F]*></font>(.*) \\((.*)\\)$", text)
            if warp_block_combat_alt_matches:
                disrupt_type, _, name, target_ship = warp_block_combat_alt_matches.groups()
                return WarpBlockCombatLine(text,  disrupt_type, "", YOU_STRING, "", name, target_ship)
            nosf_matches = re.match(
                f"{TIMESTAMP_REGEX}.*<b>.([0-9]+) GJ.*energy drained (to|from).*?<color=0x[0-9a-fA-F]*>([^(<]*?)( \\[[^]]*\\])*\\(([^)]*)\\)</b>.* - ([^<]*)</font>$",
                text)
            if nosf_matches:
                amount, incomming, source, _alliance, ship, module = nosf_matches.groups()
                return NosfCombatLine(text, amount, incomming, source, ship, module)
            nosf_alternative = re.match(f"{TIMESTAMP_REGEX}.*[-+]([0-9]+) GJ.*energy drained (to|from).*<color=0x[0-9A-Fa-f]*><b>([^<]*)</b>.*\\[([^]]*)\\] -</font>.* - ([^<]*)</font>", text)
            if nosf_alternative:
                amount, incomming, target_ship, source, module = nosf_alternative.groups()
                return NosfCombatLine(text, amount, incomming, source, target_ship, module)
            neut_matches = re.match(
                f"{TIMESTAMP_REGEX}.*<b>([0-9]+) GJ.*energy neutralized .*?<color=0x[0-9a-fA-F]*>([^([<]*)( \\[[^]]*\\])*\\(([^)]*)\\)</b>.* - ([^<]*)</font>$",
                text)
            if neut_matches:
                amount, source, _alliance, ship, module = neut_matches.groups()
                return NeutCombatLine(text, amount, source, ship, module)
            inc_logi_matches = re.match(
                f"{TIMESTAMP_REGEX}.*?<b>([0-9]*)</b>.*<font size=[0-9]*> remote (.*) by </font>.*<color=[^>]*>([^(]*)\\(([^)]*).*- ([^<]*)</font>$",
                text)
            if inc_logi_matches:
                return LogiCombatLine(text, True, *inc_logi_matches.groups())
            out_logi_matches = re.match(
                f"{TIMESTAMP_REGEX}.*<b>([0-9]*)</b>.* remote (.*) boosted to <.*<color=0x[0-9A-Fa-f]*>(([^>]*)(\\([^)]*)\\)*).*</b>.* - ([^<]*)</font>",
                text)
            if out_logi_matches:
                groups = out_logi_matches.groups()
                return LogiCombatLine(text, False, groups[0], groups[1], groups[3], groups[4], groups[5])
            inc_jam_matches = re.match(
                f"{TIMESTAMP_REGEX}.*<b>jammed</b>.*<color=0x[0-9A-Fa-f]*><b>([^<]*)</b>.* - ([^<]*)</font>", text)
            if inc_jam_matches:
                return JammedLine(text, *inc_jam_matches.groups())
            burst_matches = re.match(
                f"{TIMESTAMP_REGEX}.*target locks broken.*>by<.*<b>(([^(]*)([^)]*\\)?))</b>.* - ([^<]*)</font>", text)
            if burst_matches:
                return BurstJamLine(text, *burst_matches.groups())

            # These work as they're at the end
            npc_warp_disrupt_match = re.match(f"{TIMESTAMP_REGEX}.*Warp (scramble|disruption) attempt.*$", text)
            if npc_warp_disrupt_match:
                return CombatLine(text, True)
            npc_miss_match = re.match(f"{TIMESTAMP_REGEX} \\(combat\\) [^])>]* misses you completely$", text)
            if npc_miss_match:
                return CombatLine(text, True)
            npc_logi_matches = re.match(f"{TIMESTAMP_REGEX}.*remote [^ ]* boosted to .*", text)
            if npc_logi_matches:
                return CombatLine(text, True)

            return CombatLine(text)
        return Line(text)


class CombatLine(Line):
    def __init__(self, text, parsed=False):
        super().__init__(text, parsed)


class BurstJamLine(CombatLine):
    def __init__(self, text, _, jammer, ship, module):
        super().__init__(text, True)
        self.jammer = jammer
        self.ship = ship
        self.module = module

    def __str__(self):
        return f"Burst Jammed by {self.jammer} in {self.ship} using {self.module}"


class JammedLine(CombatLine):
    def __init__(self, text, jammer, module):
        super().__init__(text, True)
        self.jammer = jammer
        self.module = module

    def __str__(self):
        return f"Jammed by {self.jammer} using {self.module}"


class LogiCombatLine(CombatLine):
    def __init__(self, text, incomming, amount, rep_type, pilot, ship, module):
        super().__init__(text, True)
        self.amount = amount
        self.rep_type = rep_type
        self.pilot = pilot.strip()
        self.ship = ship
        self.module = module

    def __str__(self):
        return f"{self.rep_type} boosted by {self.pilot} ({self.ship}) with {self.amount} HP using {self.module}"


class NeutCombatLine(CombatLine):
    def __init__(self, text, amount, source, ship, module):
        super().__init__(text, True)
        self.amount = amount
        self.source = source.strip()
        xprint(self.source)
        self.ship = ship
        self.module = module

    def __str__(self):
        return f"{self.source} ({self.ship}) neutralized you for {self.amount} with {self.module}"


class NosfCombatLine(CombatLine):
    def __init__(self, text, amount, incomming, source, ship, module):
        super().__init__(text, True)
        self.amount = amount
        self.ship = ship
        self.source = source.strip()
        xprint(self.source)
        self.module = module

    def __str__(self):
        return f"{self.source} ({self.ship}) drained you for {self.amount} with {self.module}"


class WarpBlockCombatLine(CombatLine):
    def __init__(self, text, type, _from, source, _to, target, target_ship, source_ship=None):
        super().__init__(text, True)
        if re.match("\\(.*\\)", target_ship):
            target_ship = target_ship[1:-1]
        self.type = type
        self.source = source
        xprint(self.source) # seems to be alliance?
        self.target = target
        xprint(self.target) # alliance?
        self.target_ship = target_ship
        self.source_ship = source_ship

    def __str__(self):
        return f"Type: {self.type}, Source: {self.source}, Target: {self.target}, Ship: {self.target_ship}"


class MissCombatLine(CombatLine):
    def __init__(self, text, target, source, weapon_type=None):
        super().__init__(text, True)
        self.target = target
        xprint(self.target) # alliance
        self.source = source # source can be None!
        if self.source:
            xprint(self.source)
        self.weapon_type = weapon_type

    def __str__(self):
        return f"{self.source} missed {self.target}" + (
            f" with {self.weapon_type}!" if self.weapon_type is not None else "!")


class DamageCombatLine(CombatLine):
    def __init__(self, text, outgoing, pilot, ship, module, hit_type):
        super().__init__(text, True)
        self.outgoing = outgoing
        self.pilot = pilot
        # xprint(self.name)  ## This has () in it!
        self.module = module # TODO: parse

    def __str__(self):
        return f"{self.outgoing}, {self.pilot}, {self.module}"


def xprint(line):
    if line == YOU_STRING:
        return
    if "!" not in line and "[" not in line and not "belonging to" in line and not "(" in line:
        Cache.get_instance().get_missing([line])
       # print(line)
    else:
        raise IndexError

def is_valid_line(line):
    if not is_log_line(line):
        return False

    return True


def test_follow(filename):
    for line in filename:
        if is_valid_line(line):
            yield line


def follow(filename):
    filename.seek(0, 2)
    while True:
        try:
            line = filename.readline()
            if not line:
                time.sleep(0.1)
                continue
            if is_valid_line(line):
                yield line
        except UnicodeDecodeError as e:
            print(f"UnicodeDecodeError: {e} - Skipping line")


if TESTING:
    follow = test_follow


def parse(path):
    logfile = open(path, "r", encoding="unicode_escape")
    has_print = False
    for line in follow(logfile):
        data = Line.parse(line)
        if not data.parsed and isinstance(data, CombatLine):
            has_print = True
            print(data)
        if isinstance(data, CombatLine):
            print(data)
    return has_print


if __name__ == '__main__':
    for filename in os.listdir("C:/Users/Aitesh/Documents/EVE/logs/Gamelogs/"):
        if not filename.startswith("20240206_114231_788408631"):
            continue
        try:
            if parse(rf"C:/Users/Aitesh/Documents/EVE/logs/Gamelogs/{filename}"):
                print(f"^: {filename}")
        except UnicodeDecodeError:
            print(f"UnicodeDecodeError: {filename} - Skipping")
        Cache.get_instance().save()
    Cache.get_instance().download_all_images()
    Cache.get_instance().wait_for_threads()
    Cache.get_instance().save()
