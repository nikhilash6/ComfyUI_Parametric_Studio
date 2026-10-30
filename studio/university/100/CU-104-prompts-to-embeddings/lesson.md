# CU-104 - Prompts become numbers: tokens and embeddings

**Objective.** Follow a prompt from text to the tensor the sampler receives: split it into tokens, look the tokens up in a table of vectors, and say what the text encoder's attention adds to that table. Taught by Madame Attention.

## The idea

The image model never reads your sentence. ComfyUI cuts the text into tokens, replaces each token by a row of a table, and runs those rows through a text transformer. What reaches the sampler is one vector per token position, a tensor of shape [positions, width], and the denoiser's cross-attention looks at those vectors. Three steps, then: tokenise, look up, let the tokens attend to each other.

## The mechanism

**Tokens.** Words are the wrong unit, because there are too many of them. Byte-pair encoding, an old compression trick that Sennrich et al. (2015) adapted to words, starts from single characters plus an end-of-word symbol, finds the most frequent neighbouring pair, fuses it into a new symbol, and repeats. The number of merges is the only setting, and the vocabulary size is the starting symbols plus the merges. To split a new word, apply the merges in the order they were learned. Common words end up as one token, and rare words fall apart into pieces. CLIP's tokenizer lowercases the text and works on UTF-8 bytes, so no input is unknown to it, and it adds a start marker and an end marker.

**Lookup.** Token ids index a matrix E with one row per token. Reading row i is the same as multiplying a one-hot vector by E. CLIP adds a second table, one row per position, so the same word at another position gets another vector. The row for a token does not know its neighbours.

**Attention.** Attention(Q, K, V) = softmax(Q Kᵀ / √d_k) V (Vaswani et al. 2017). Each position builds a query, compares it with every key, turns the scores into weights with a softmax, and mixes the values. CLIP's text encoder uses masked self-attention, which sets the scores of later positions to −∞ before the softmax. Position i then sees only positions up to i, so the vector at the end marker is the first one that has seen the whole prompt. CLIP takes that vector, after a layer norm, as the summary of the text (Radford et al. 2021).

## In ComfyUI

`CLIPTextEncode` calls `clip.tokenize(text)` and `clip.encode_from_tokens_scheduled(tokens)`. The result, CONDITIONING, is a list of pairs: a tensor with one vector per position, and a dictionary holding `pooled_output`, the encoder's output at the end marker.

`SDTokenizer` in `comfy/sd1_clip.py` uses Hugging Face's `CLIPTokenizer` with the vocabulary and merge files in `comfy/sd1_tokenizer`. The vocabulary file has 49,408 entries, the start marker is 49406 and the end marker 49407. The text encoder has 77 positions, so a chunk is a start marker, up to 75 tokens, an end marker and padding. ComfyUI does not truncate a longer prompt. It cuts the tokens into chunks, encodes each chunk as its own sequence, and joins the results along the sequence axis. Words in different chunks never attend to each other.

Weights such as `(sunset:1.3)` are applied after encoding. The prompt is encoded together with an empty prompt, and each weighted position moves away from the empty-prompt vector: z becomes (z − z_empty) × w + z_empty. Plain parentheses mean 1.1.

The width depends on the family. SD 1.x uses CLIP ViT-L: 12 layers and width 768, so a short prompt gives [1, 77, 768]. SDXL uses two encoders, CLIP ViT-L and OpenCLIP ViT-bigG, and concatenates their penultimate-layer outputs along the channel axis, 768 + 1280 = 2048 (Podell et al. 2023, and `comfy/sdxl_clip.py`). It also passes the pooled output of the bigG model. Flux sends the sequence from a T5 encoder and only the pooled vector from CLIP-L.

## Lab

Part one learns byte-pair merges on the four-word vocabulary of the paper's own listing (low five times, lower twice, newest six times, widest three times), then splits words with them.

```text
merges learned, in order: e+s, es+t, est+</w>, l+o, lo+w, n+e, ne+w, new+est</w>, low+</w>, w+i
```

```text
word      pieces
low       low</w>
newest    newest</w>
lowest    low est</w>
wider     wi d e r </w>
newer     new e r </w>
slow      s low</w>
```

"lowest" never occurred in training, yet it splits into two pieces the merges already know. "wider" costs five pieces because the merges barely cover it. This toy starts from characters, and CLIP's real merges are not these.

Part two uses random weights, so it can only show what holds for any weights. A tiny vocabulary, a table E, position rows, and one head of causal attention.

```text
lookup: one-hot vector times the table, against reading the row; largest difference over all ids: 0.0
'bank' after 'river' against 'bank' after 'money':
  table row plus position, before attention: largest difference 0.000000
  output of one causal attention layer:      largest difference 0.998983
'river' in 'river bank' against 'river sat' (only the next word differs):
  with the causal mask:    largest difference 0.000000
  without the mask:        largest difference 0.933489
output at the end marker, 'river bank' against 'money bank': largest difference 0.711494
```

The table row for "bank" is identical in both prompts, and the output of the attention layer is not, because it mixes in the earlier words. With the causal mask, "river" is untouched by the word after it. Remove the mask and it changes. The end marker, which sees everything before it, differs between the two prompts, which is why it can serve as the summary.

Part three is arithmetic on ComfyUI's chunk rule for prompts of one-token words, with the widths from the two CLIP configuration files.

```text
tokens in prompt  chunks   SD 1.x conditioning     SDXL conditioning (768 + 1280 wide)
5                 1        [1, 77, 768]            [1, 77, 2048]
75                1        [1, 77, 768]            [1, 77, 2048]
76                2        [1, 154, 768]           [1, 154, 2048]
100               2        [1, 154, 768]           [1, 154, 2048]
150               2        [1, 154, 768]           [1, 154, 2048]
```

The 75th token fits in the first chunk and the 76th opens a second one. These rows follow from reading the code, not from running ComfyUI. Words made of several tokens can leave a chunk short, because a short word that does not fit moves to the next chunk.

## What is contested

With random weights the lab shows structure, not meaning. Whether a trained encoder puts related prompts close together is a question about trained weights, and nothing here measures it, so do not read the numbers as similarity scores. The CLIP paper states a cap of 76 on the sequence length, while ComfyUI's configurations use 77 positions, which is a start marker, 75 tokens and an end marker. How much a late chunk influences the picture is an empirical question, and this lesson only establishes that chunks are encoded separately.

## Sources

- [Sennrich, Haddow, Birch 2015. Neural Machine Translation of Rare Words with Subword Units](https://arxiv.org/abs/1508.07909)
- [Radford et al. 2021. Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Podell et al. 2023. SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952)
- [OpenAI CLIP, clip/simple_tokenizer.py](https://github.com/openai/CLIP/blob/3bee28119e6b28e75b82b811b87b56935314e6a5/clip/simple_tokenizer.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd1_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip.py)
- [ComfyUI v0.43.0, comfy/clip_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/clip_model.py)
- [ComfyUI v0.43.0, comfy/sdxl_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sdxl_clip.py)
- [ComfyUI v0.43.0, comfy/text_encoders/flux.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/flux.py)
- [ComfyUI v0.43.0, comfy/sd1_clip_config.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip_config.json)
- [ComfyUI v0.43.0, comfy/clip_config_bigg.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/clip_config_bigg.json)
- [ComfyUI v0.43.0, comfy/sd1_tokenizer/vocab.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_tokenizer/vocab.json)
