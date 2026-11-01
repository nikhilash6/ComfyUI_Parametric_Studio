# CU-383 - Licences in practice: AGPL, GPL, MIT, OpenRAIL

**Objective.** Read a licence for the case you're actually in: using it at home, changing it, giving a copy, or running a service. This is not legal advice. Taught by Captain Graph.

## The first question: what are you doing with it?

Licences mostly attach to specific acts. Before you read a licence, know your act. Running software at home is rarely where the duties are. They usually wake up when you hand a copy to someone, or, for one licence, serve it to them.

We read each text below and quote it where the wording matters. We aren't lawyers. If real money or a real product depends on it, ask one.

## MIT

Short enough to read in a minute. You can use, copy, change, sell. The one condition: "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software." Keep the notice when you pass it on, and you're done. Apache-2.0 is similar with more steps: keep notices, and "cause any modified files to carry prominent notices stating that You changed the files".

## GPL-3.0

ComfyUI itself is under this. You can run and change it freely at home. The duties attach to **conveying**, which means giving copies. Section 5 asks that a modified version carries notices of your change and stays under this licence. And the source has to be available to those who get it.

Section 0 draws an important line: "Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying." So running a changed GPL program on your server, for people who use it through a browser, doesn't by that alone trigger the source duty.

## AGPL-3.0

The same as GPL, with one addition, which is section 13: "if you modify the Program, your modified version must prominently offer all users interacting with it remotely through a computer network ... an opportunity to receive the Corresponding Source". That closes the gap above. If you changed an AGPL pack and strangers use it through your website, offer them your source.

Note its conditions. It says modify, and it says users interacting remotely. Running it unmodified, or changing it just for yourself, doesn't trigger this section.

## CreativeML Open RAIL-M

This is a model licence, and a different kind of thing. It's broad, and some uses are written out of it. Paragraph 5 says "You cannot use the Model and the Derivatives of the Model for the specified restricted uses", which are listed in Attachment A. Those limits apply to you even at home, unlike the others above. Paragraph 4 covers hosting for others as well as distributing, and says the restrictions must be passed on in your own terms. On output, paragraph 6 says the licensor "claims no rights in the Output You generate", and you're accountable for how you use it.

{{play:licence}}

## No licence at all

This surprises people. A public repository without a licence isn't free to use. The usual reading, as choosealicense.com puts it, is that it "generally means you have no permission from the creators of the software to use, modify, or share the software". Ask the author for one, or use something else. Reading the code to understand a method is one thing, and copying it is another.

## A graph is several works

One graph can touch several sets of terms. Read each one for what you're doing with it.

{{graph:sd15_lora}}

## In practice

- **Check the LICENSE file itself.** A README badge can differ. A pack can add clauses, such as a commercial limit next to a standard licence.
- **Check model pages too.** Model weights often have their own terms, separate from the code that runs them.
- **Taking an idea is different from taking code.** If you need the behaviour of a GPL or unlicensed pack in a differently licensed project, the safe path is usually your own implementation from the idea or the paper, written without copying. Ask someone qualified where this matters.
- **Keep a list.** For anything you ship: part, version, licence, and what you did to meet it.

## What goes wrong

- **"GPL means I have to publish everything I make with it."** The pictures you make aren't covered by that, and running it at home triggers nothing. Read section 5 for what conveying asks.
- **Assuming AGPL is banned for any use.** It asks something specific in a specific case. Read section 13 for your case.
- **Copying a function from an MIT pack and dropping the notice.** That's the one condition. Keep it.
- **Treating "no licence" as "free".** It's closer to the opposite.
- **Reading a summary, including this one, instead of the text.** Licences change between versions, and packs add clauses.

## Lab

The lab holds short quotes, and a small function for our reading of each case. It's a study aid, not advice.

```text
GPL-3.0 s0     Mere interaction with a user through a computer network, with no transfer of a copy, is not conv
AGPL-3.0 s13   your modified version must prominently offer all users interacting with it remotely through a co
MIT            The above copyright notice and this permission notice shall be included in all copies or substan
OpenRAIL-M 5   You cannot use the Model and the Derivatives of the Model for the specified restricted uses.
```

```text
MIT
  use as is, at home                     nothing triggered
  change it, at home                     nothing triggered
  change it, give a friend a copy        keep notice
  change it, run a site for strangers    nothing triggered
  as is, run a site for strangers        nothing triggered
```

AGPL differs from GPL in one row, the changed copy on a site for strangers, where GPL triggers nothing. A reading is only as good as the row you are really in:

```text
AGPL-3.0
  use as is, at home                     nothing triggered
  change it, at home                     nothing triggered
  change it, give a friend a copy        give source, keep licence, mark changes
  change it, run a site for strangers    offer source to remote users
  as is, run a site for strangers        nothing triggered
```

```text
OpenRAIL-M
  use as is, at home                     no banned uses
  change it, at home                     no banned uses
  change it, give a friend a copy        no banned uses; pass the use limits on
  change it, run a site for strangers    no banned uses; pass the use limits on
  as is, run a site for strangers        no banned uses; pass the use limits on

copying a piece of a pack into your own project, by the pack's licence
  MIT                allowed, keep the notice
  Apache-2.0         allowed, keep notices and state changes
  GPL-3.0            your work that contains it, if you convey it, comes under GPL-3.0
  AGPL-3.0           as GPL, plus the remote-users offer if modified
  no licence file    no permission has been given: write your own
```



## Sources

- [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.txt)
- [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.txt)
- [MIT licence text, SPDX](https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt)
- [Apache-2.0 licence text, SPDX](https://raw.githubusercontent.com/spdx/license-list-data/main/text/Apache-2.0.txt)
- [CreativeML Open RAIL-M, text from CompVis](https://huggingface.co/spaces/CompVis/stable-diffusion-license/raw/main/license.txt)
- [No Permission, choosealicense.com](https://choosealicense.com/no-permission/)
- [ComfyUI v0.43.0, LICENSE](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/LICENSE)
