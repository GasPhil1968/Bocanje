"""Render the TRI FILDŽANA SFX pack: python3 build.py <out_dir>"""
import sys, os, json, zlib
import sounds as S
from core import *

# id, function, variants, duration range (s), target max-momentary loudness (LUFS),
# recommended playback gain, category, game event
CAT = [
 ('cup_set_down', S.cup_set_down, 4, (0.10, 0.25), -27, 0.85, 'cups', 'A cup lands on the table: end of every swap, cups placed in the intro, Hakala/Levat/wind settling a cup.'),
 ('cup_slide', S.cup_slide, 4, (0.15, 0.35), -31, 0.8, 'cups', 'Start of each real or fake swap (one per swap, random variant).'),
 ('cup_lift', S.cup_lift, 2, (0.10, 0.20), -32, 0.9, 'cups', 'A cup is lifted: SHOW start, REVEAL lift of the picked cup, truth reveal lift, Hakala check.'),
 ('cup_select', S.cup_select, 1, (0.08, 0.15), -28, 0.9, 'cups', 'Player taps a cup (doPick).'),
 ('cup_rattle', S.cup_rattle, 2, (0.20, 0.45), -27, 0.9, 'cups', 'Cup tilted/knocked (Levat bump tilt), packed (inventura flee), confiscated (raid).'),
 ('table_bump', S.table_bump, 1, (0.25, 0.50), -23, 1.0, 'cups', 'Levat "accidentally" bumps the table after a bribe.'),
 ('ball_reveal', S.ball_reveal, 1, (0.20, 0.40), -22, 0.9, 'cups', 'The ball\'s real location is shown after a wrong pick (shownTruth).'),
 ('cheat_glint', S.cheat_glint, 1, (0.12, 0.25), -21, 0.9, 'cups', 'Visible cheating tell flash during a swap (G.tell).'),
 ('ui_confirm', S.ui_confirm, 1, (0.08, 0.15), -25, 0.9, 'ui', 'Menu / option / start / language / stats / share buttons.'),
 ('bet_place', S.bet_place, 1, (0.25, 0.45), -26, 0.9, 'money', 'Bet chip pressed -> round starts (startRound).'),
 ('banknotes_count', S.banknotes_count, 1, (0.60, 1.00), -27, 0.9, 'money', 'Intro variant 0: Šaner caught counting money.'),
 ('money_handover', S.money_handover, 1, (0.30, 0.60), -29, 0.9, 'money', 'Bribe handed over: to Levat (levmito) or to the police (mito accepted/too small).'),
 ('coins_small', S.coins_small, 1, (0.25, 0.45), -25, 0.9, 'money', 'Small coin moment: Levat bribe, advert interlude hit.'),
 ('coins_large', S.coins_large, 1, (0.50, 0.80), -23, 0.9, 'money', 'Coin payout on a win (spawnCoin x14), accepted police bribe (coins fly), table overturn coins.'),
 ('round_win', S.round_win, 1, (0.70, 1.00), -17, 1.0, 'result', 'Round won (resolve, G.won); New-Year special start.'),
 ('round_lose', S.round_lose, 1, (0.45, 0.70), -19, 1.0, 'result', 'Round lost (resolve, !G.won).'),
 ('game_over', S.game_over, 1, (1.20, 1.70), -18, 1.0, 'result', 'Out of money (toOver) / arrested (toUhapsen).'),
 ('escape_victory', S.escape_victory, 1, (1.00, 1.50), -16, 1.0, 'result', 'Šaner gave up and fled: level won (toPobjeda).'),
 ('bribe_rejected', S.bribe_rejected, 1, (0.25, 0.45), -20, 1.0, 'result', 'Police bribe refused/too small, or nobody answered (mito timeout).'),
 ('saner_annoyed', S.saner_annoyed, 2, (0.40, 0.80), -24, 0.85, 'voice', 'Šaner annoyed: poked, idle grumble, player waits too long, Hakala heckles.'),
 ('saner_angry', S.saner_angry, 2, (0.30, 0.65), -23, 0.85, 'voice', 'Šaner angry after the player wins (RESULT 1.0-3.6 s), Ćiro chased away.'),
 ('saner_nervous', S.saner_nervous, 1, (0.35, 0.65), -26, 0.85, 'voice', 'Nervousness level rises (G.nerv increases).'),
 ('saner_gasp', S.saner_gasp, 1, (0.20, 0.45), -22, 0.9, 'voice', 'Police arrive (toRacija), intro "are we recording?!", Minka phone panic.'),
 ('saner_chuckle', S.saner_chuckle, 2, (0.50, 0.90), -24, 0.85, 'voice', 'Šaner gloats after the player loses (saner_gloat frames at RESULT 2.95 s).'),
 ('saner_wipe_forehead', S.saner_wipe_forehead, 1, (0.35, 0.65), -33, 0.8, 'voice', 'Sweat-wipe animation starts (saner_wipe_* frames).'),
 ('saner_poke', S.saner_poke, 1, (0.20, 0.40), -23, 0.9, 'voice', 'Player taps Šaner (pokeSaner).'),
 ('levat_reaction', S.levat_reaction, 1, (0.30, 0.60), -24, 0.85, 'voice', 'Levat peeks in with a puzzled comment / leaves.'),
 ('minka_attention', S.minka_attention, 1, (0.30, 0.60), -24, 0.9, 'voice', 'Minka arrives in person (minkaSeen).'),
 ('audience_murmur', S.audience_murmur, 1, (0.60, 1.20), -26, 0.8, 'voice', 'Hakala heckles from the audience, Ćiro shouts a tip, audience reacts.'),
 ('coffee_activate', S.coffee_activate, 1, (0.45, 0.75), -23, 0.9, 'powerup', 'Coffee power-up (shuffle at 55 % speed).'),
 ('eye_activate', S.eye_activate, 1, (0.25, 0.45), -23, 0.9, 'powerup', 'Eye power-up (vision aid).'),
 ('pigeon_coo', S.pigeon_coo, 2, (0.50, 0.90), -26, 0.85, 'pigeon', 'Pigeon perches on a cup / paid pigeon power-up.'),
 ('pigeon_wings', S.pigeon_wings, 2, (0.30, 0.60), -26, 0.85, 'pigeon', '_01 departure (bird leaves), _02 arrival (bird flies in).'),
 ('wind_gust', S.wind_gust, 1, (0.70, 1.00), -24, 1.0, 'ambience', 'Night-scene gust that shifts the cups (G.vjetar).'),
 ('police_siren', S.police_siren, 1, (2.40, 2.60), -17, 1.0, 'police', 'Raid starts (toRacija); Šaner taken away (toOdveli).'),
 ('police_step', S.police_step, 4, (0.12, 0.25), -24, 0.9, 'police', 'Police walk in (RACIJA entry) and escort steps (UHAPSEN/ODVELI escort frames).'),
 ('police_grab', S.police_grab, 1, (0.20, 0.40), -24, 0.95, 'police', 'Police grab Šaner (grab frames / MILICIJA_UVOD / no-answer arrest).'),
 ('police_warning', S.police_warning, 1, (0.35, 0.60), -19, 1.0, 'police', 'Bribe demand appears (pokreniMito).'),
 ('run_step', S.run_step, 4, (0.07, 0.14), -27, 0.8, 'escape', 'Each fleeRun footstep (every 0.17 s).'),
 ('table_overturn', S.table_overturn, 1, (0.60, 0.90), -18, 1.0, 'escape', 'Flee variant "sto": table tipped over.'),
 ('cups_scatter', S.cups_scatter, 1, (0.40, 0.70), -22, 1.0, 'escape', 'Flee variant "sto": cups fly off the table.'),
 ('cloth_swish', S.cloth_swish, 1, (0.30, 0.50), -23, 1.0, 'escape', 'Flee variant "inventura": rug/cloth pulled away.'),
 ('bundle_pack', S.bundle_pack, 1, (0.45, 0.75), -25, 1.0, 'escape', 'Flee variant "inventura": cups packed into the waistcoat/bundle.'),
 ('smoke_puff', S.smoke_puff, 1, (0.65, 0.90), -20, 1.0, 'escape', 'Flee variant "dim": smoke bomb.'),
 ('distraction_whistle', S.distraction_whistle, 1, (0.25, 0.40), -21, 1.0, 'escape', 'Flee variant "milicija": fake police warning.'),
 ('escape_swish', S.escape_swish, 1, (0.20, 0.35), -24, 1.0, 'escape', 'Quick disappearance (milicija flash, dim fade, start of run).'),
 ('tv_switch_on', S.tv_switch_on, 1, (0.25, 0.45), -22, 1.0, 'tv', 'Intro cue 1 (TV switched on).'),
 ('tv_test_tone', S.tv_test_tone, 1, (1.44, 1.46), -28, 0.8, 'tv', 'Intro cue 2 (test card tone).'),
 ('tv_static_cut', S.tv_static_cut, 1, (0.25, 0.50), -24, 1.0, 'tv', 'Intro cue 3 (non-clapper intros), news/2nd-news interludes.'),
 ('film_clapper', S.film_clapper, 1, (0.15, 0.30), -18, 1.0, 'tv', 'Intro variant 1 clapper; interlude 0 (klapa) hit.'),
 ('telephone_ring', S.telephone_ring, 1, (0.70, 1.20), -21, 0.9, 'tv', 'Minka calls (startRound minka===1); interlude 4 (telefon).'),
 ('telephone_pickup', S.telephone_pickup, 1, (0.15, 0.30), -24, 1.0, 'tv', 'Intro variant 2 phone beat; interlude 4 hit.'),
 ('title_sting', S.title_sting, 1, (0.70, 1.00), -17, 1.0, 'tv', 'Intro cue 7: title appears.'),
 ('scene_transition', S.scene_transition, 1, (0.70, 1.00), -19, 1.0, 'tv', 'Interlude cut to the next location (medjuCue 3).'),
 ('advert_sting', S.advert_sting, 1, (0.60, 0.90), -19, 1.0, 'tv', 'Advert interludes 2 and 11.'),
 ('news_sting', S.news_sting, 1, (0.60, 0.90), -18, 1.0, 'tv', 'News interludes 3 and 7; Levat newsreader intro (variant 3).'),
 ('moving_rumble', S.moving_rumble, 1, (0.40, 0.70), -24, 1.0, 'tv', 'Interlude 1 (selidba / moving).'),
 ('paper_map', S.paper_map, 1, (0.25, 0.45), -26, 1.0, 'tv', 'Interlude 5 (karta puta / route map).'),
 ('transition_swish', S.transition_swish, 1, (0.25, 0.40), -26, 1.0, 'tv', 'Generic interlude opener (6 sjednica, 8 audicija, 9 pauza, 10 gost).'),
]
STEREO = {'round_win', 'round_lose', 'game_over', 'escape_victory', 'title_sting', 'scene_transition', 'advert_sting',
          'news_sting', 'police_warning', 'audience_murmur'}


FAIL = []
ONLY = os.environ.get('ONLY')


def render_all(out):
    sfx = os.path.join(out, 'audio', 'sfx')
    entries = []
    for sid, fn, nv, rng_d, loud, gain, cat, ev in CAT:
        if ONLY and sid not in ONLY.split(','):
            continue
        vars_ = []
        for v in range(nv):
            fname = f'{sid}_{v + 1:02d}.wav' if nv > 1 else f'{sid}.wav'
            seed = zlib.crc32(fname.encode())
            r = rng(seed)
            x = fn(r, v)
            # tail threshold: loose for long musical tails, tight for short Foley
            try:
                x = finish(x, rng_d, loud=loud, tail_db=-60 if sid not in STEREO else -50,
                           fout=0.006 if rng_d[1] <= 0.25 else 0.02)
            except AssertionError as e:
                print('!!', fname, e); FAIL.append(fname); continue
            write16(os.path.join(sfx, fname), x, rng(seed + 1))
            vars_.append(fname)
            print(f'{fname:32s} {len(x) / SR:6.3f}s  {"st" if x.ndim > 1 else "mono"}  {db(true_peak(x)):6.2f} dBTP  {loud_m(x):6.1f} LUFS(M)')
        entries.append(dict(id=sid, category=cat, files=vars_, duration_range=rng_d, target_loudness=loud,
                            gain=gain, event=ev))
    return entries


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ent = render_all(out)
    print('FAILED:', FAIL)
    json.dump(ent, open(os.path.join(out, '_render.json'), 'w'), indent=1, ensure_ascii=False)
