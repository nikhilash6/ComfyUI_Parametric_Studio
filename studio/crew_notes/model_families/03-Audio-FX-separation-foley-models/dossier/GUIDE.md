# Sound effects and short sounds: what makes one land (checked 2026-11-03)

This is research on short sounds, rewritten in plain words: stings, impacts, reaction clips and voice lines. It came from a literature review done for the studio this one grew from, with every claim graded. Nothing here was re-run for this studio. Where this file and older notes in this folder disagree on how to write or shape a sound, this file wins. [inference]

Labels: a paper named in a claim label was read at least as an abstract by the earlier review, not by us. "Earlier studio" means a measurement taken on that studio's own renders. A sentence with only an inference label is our reasoning, often a starting value nobody has tested. [inference]

## The one thing to say first

Craft raises the odds that a sound works. It cannot predict that a sound will spread. Social influence makes popularity unequal and hard to predict, in a music market experiment with 14,341 people. Across a billion sharing events on one social network, over 99% of cascades stayed tiny, and big spread is mostly one broadcast rather than friend to friend. Never present a sound score as a chance of going viral. [claim: Salganik, Dodds and Watts 2006, Science] [claim: Goel et al. 2016, Management Science]

No published study measures what makes a sting, a reaction clip or a voice meme spread. The advice below for those classes rests on how hearing works (startle, looming, roughness, repetition) plus inference, and says so. [claim: earlier studio literature review, 2026-10-17] [inference]

## What the research supports

Startle comes from the onset, not the loudness. A fast, broadband attack triggers it, and rise time, level and bandwidth all change how strongly. This is the basis for an impact sting. Using it for meme stings is our inference. [claim: Blumenthal and Berg 1986, Psychophysiology] [inference]

A sound that rises in level before a hit makes the hit land harder. People over-estimate the loudness change of rising sounds at high levels, 70 to 90 dB SPL. So a riser before an impact is supported, not a superstition. [claim: Olsen and Stevens 2010, Perception]

Roughness is the alarm cue. Amplitude modulation between about 30 and 150 Hz is the shared signature of screams and alarms. It raises detection and fear ratings and drives the amygdala. A harsh, buzzing texture reads as danger; a smooth one does not. [claim: Arnal et al. 2015, Current Biology]

Repetition turns speech into song. After about ten exact repeats a spoken phrase starts to sound sung, more so when the pitch inside each syllable is steady. This has been replicated across labs and is the strongest known mechanism behind a looped voice line. [claim: Tierney, Patel and Breen 2018, Journal of Experimental Psychology: General] [claim: Falk, Rathcke and Dalla Bella 2014, "When speech sounds like music"]

Short sounds are recognised fast. Listeners named the genre of 250 ms clips above chance, and named artist and title on over a quarter of 400 ms clips. Repeated noise snippets are learned quickly without effort. A sound has a fraction of a second to say what it is. [claim: Gjerdingen and Perrott 2008, Journal of New Music Research] [claim: Krumhansl 2010, Music Perception]

Contagious laughs have a faster burst rate, a higher and more variable pitch and a brighter spectrum. That is one preprint of 149 laughs and 1,509 raters, so treat it as a lead. [claim: contagious laughter preprint 2025, OSF cnqs4]

## Claims to ignore

These come up often and have no good source: an "8-second attention span"; "the comic pause makes the joke" (it failed three tests); "using a trending sound makes the platform boost you" (the platforms' own pages say nothing of the kind); "viral songs average 19.5 s"; "sounds last 5 to 14 days"; and a fixed "-14 LUFS for short-video apps". [claim: earlier studio literature review, 2026-10-17]

The one official loudness figure found was from a music streaming service: it normalises to -14 LUFS integrated and keeps 1 dB of headroom for lossy encoding. No short-video app publishes a target. Vendor blogs disagree, from -14 down to -10. [claim: Spotify loudness normalization help page] [claim: earlier studio literature review, 2026-10-17]

## A checklist for each kind of sound

Sting or impact: a sharp, broadband onset, a short decay, some sub-bass body, an optional riser before it, and room after it. A starting band to calibrate from: 0.3 to 2.5 s long, an attack under 10 ms, the peak within 50 ms, and decay to -30 dB within 0.2 to 1.5 s. Those numbers are our suggestion, not a finding. [claim: earlier studio literature review, 2026-10-17] [inference]

Reaction clip: dry and close, with no music bed, 0.5 to 3 s for a single beat, so it can be cut straight onto a picture. [inference]

Voice line: a clear cadence, steady pitch inside each syllable, a short quotable phrase of 1 to 6 s, and a clean loop. Steady syllable pitch is the part with evidence behind it. [claim: Tierney, Patel and Breen 2018] [inference]

Packaging for any short sound: clear points to cut to, a loop-ready export, and a short, plain name. [inference]

## Mixing a sound into a clip

When a sting plays over a music bed, dip the bed about 6 dB under the sting and set the sting about -8 dB. A voice line sits 6 to 8 dB under the main speaker and only in a gap in their speech. Put the action the sound punctuates in the video prompt (the door slams, the cut to the reaction), not a description of the sound itself. These rules came from the earlier studio's sound cards and were never measured. [claim: earlier studio sound cards, 2026-10-17] [inference]

Writer rules the earlier review proposed, all untested: place a cue on a sync point (a cut, a drop, a punchline), put a riser before an impact, never stack two stings, keep voice-like sounds off speech, and keep cues sparse. [claim: earlier studio literature review, 2026-10-17] [inference]

This studio's mastering already follows the delivery side of this: voice over music is ducked by drawing a volume curve from the speech sections, then mastered to -14 LUFS with the true peak at or under -1 dBTP, read from ffmpeg's own meters. [code: studio/audio_master.py:1-7]

## What measuring a sound cannot tell you

A meter cannot see why a sound works: the picture it is cut to, the joke, who posted it, what the audience has already heard, or how it sounds on a phone speaker. A sound checker built from the measurements above is a quality check for its class (onset, length, loudness, repetition, no clicks), never a forecast. [claim: earlier studio literature review, 2026-10-17] [inference]
