"""Not Dao-AILab's flash-attn: the six calls TRELLIS.2 makes of it, on torch's own scaled_dot_product_attention (which
picks its flash or memory-efficient kernel itself), so no compiled wheel from a third-party account is needed.

Variable-length calls take sequences packed end to end ((total, heads, dim) with cumulative lengths): a few sequences
(the full attention of one model, two with guidance) are attended one at a time unmasked; many (TRELLIS.2's windowed
attention, thousands of short windows) are padded into one batch with their keys masked.
"""
import torch
import torch.nn.functional as functional

FEW = 8  # up to this many sequences are attended one by one


def heads_first(tensor):
    """(batch, length, heads, dim) as (batch, heads, length, dim)."""
    return tensor.transpose(1, 2)


def attended(query, key, value, scale=None, causal=False):
    """(batch, length, heads, dim) attention of query over key and value, in that layout."""
    out = functional.scaled_dot_product_attention(heads_first(query), heads_first(key), heads_first(value),
                                                  is_causal=causal, scale=scale)
    return heads_first(out)


def padded(packed, starts, lengths, longest):
    """Packed (total, heads, dim) rows as (sequences, longest, heads, dim), zero past each length; the valid mask."""
    places = torch.arange(longest, device=packed.device)
    valid = places[None, :] < lengths[:, None]
    rows = (starts[:, None] + places[None, :]).clamp(max=packed.shape[0] - 1)
    batch = packed[rows]
    return batch * valid[:, :, None, None].to(batch.dtype), valid


def varlen(query, key, value, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, softmax_scale=None,
           causal=False, **ignored):
    """flash_attn_varlen_func: (total_q, heads, dim) out."""
    count = cu_seqlens_q.shape[0] - 1
    if count <= FEW:
        bounds_q, bounds_k = cu_seqlens_q.tolist(), cu_seqlens_k.tolist()
        return torch.cat([attended(query[bounds_q[at]:bounds_q[at + 1]][None], key[bounds_k[at]:bounds_k[at + 1]][None],
                                   value[bounds_k[at]:bounds_k[at + 1]][None], softmax_scale, causal)[0]
                          for at in range(count)])
    lengths_q, lengths_k = cu_seqlens_q[1:] - cu_seqlens_q[:-1], cu_seqlens_k[1:] - cu_seqlens_k[:-1]
    batch_q, valid_q = padded(query, cu_seqlens_q[:-1].long(), lengths_q.long(), int(max_seqlen_q))
    batch_k, valid_k = padded(key, cu_seqlens_k[:-1].long(), lengths_k.long(), int(max_seqlen_k))
    batch_v, _ = padded(value, cu_seqlens_k[:-1].long(), lengths_k.long(), int(max_seqlen_k))
    mask = valid_k[:, None, None, :]
    out = functional.scaled_dot_product_attention(heads_first(batch_q), heads_first(batch_k), heads_first(batch_v),
                                                 attn_mask=mask, scale=softmax_scale)
    return heads_first(out)[valid_q]


def flash_attn_varlen_func(q, k, v, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, **options):
    return varlen(q, k, v, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, **options)


def flash_attn_varlen_kvpacked_func(q, kv, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, **options):
    return varlen(q, kv[:, 0], kv[:, 1], cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, **options)


def flash_attn_varlen_qkvpacked_func(qkv, cu_seqlens, max_seqlen, **options):
    return varlen(qkv[:, 0], qkv[:, 1], qkv[:, 2], cu_seqlens, cu_seqlens, max_seqlen, max_seqlen, **options)


def flash_attn_func(q, k, v, softmax_scale=None, causal=False, **ignored):
    return attended(q, k, v, softmax_scale, causal)


def flash_attn_kvpacked_func(q, kv, softmax_scale=None, causal=False, **ignored):
    return attended(q, kv[:, :, 0], kv[:, :, 1], softmax_scale, causal)


def flash_attn_qkvpacked_func(qkv, softmax_scale=None, causal=False, **ignored):
    return attended(qkv[:, :, 0], qkv[:, :, 1], qkv[:, :, 2], softmax_scale, causal)
