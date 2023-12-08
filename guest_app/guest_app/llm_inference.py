# from transformers import (
#     AutoTokenizer,
#     LlamaForCausalLM,
#     PreTrainedTokenizer,
#     PreTrainedTokenizerFast,
# )
# from tqdm import tqdm
# import torch

# # initialize the model

# models_dir_path = "/home/guest/nvtrust-private/guest_app/models"
# model_path = models_dir_path + "/" + "Phind-CodeLlama-34B-v2"


# def init_model():
#     model = LlamaForCausalLM.from_pretrained(
#         model_path, device_map=0, torch_dtype=torch.float16
#     )
#     tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)
#     return model, tokenizer


# # HumanEval helper


# def generate_one_completion(
#     model: LlamaForCausalLM,
#     tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast,
#     prompt: str,
# ) -> str:
#     tokenizer.pad_token = tokenizer.eos_token
#     inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)

#     # Generate
#     generate_ids = model.generate(
#         inputs.input_ids.to("cuda"),
#         max_new_tokens=384,
#         do_sample=False,
#         top_p=0.75,
#         top_k=40,
#         temperature=0.1,
#         pad_token_id=tokenizer.eos_token_id,
#     )
#     completion = tokenizer.batch_decode(
#         generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
#     )[0]
#     completion = completion.replace(prompt, "").split("\n\n\n")[0]

#     return completion


# num_samples_per_task = 1
# samples = [
#     dict(
#         task_id=task_id, completion=generate_one_completion(problems[task_id]["prompt"])
#     )
#     for task_id in tqdm(problems)
#     for _ in range(num_samples_per_task)
# ]
# write_jsonl("samples.jsonl", samples)

# from transformers import AutoModelForCausalLM, AutoTokenizer
# import torch

# models_dir_path = "/home/guest/nvtrust-private/guest_app/models"
# model_name_or_path = models_dir_path + "/" + "Phind-CodeLlama-34B-v2-GPTQ"


# def init_model():
#     # To use a different branch, change revision
#     # For example: revision="gptq-4bit-32g-actorder_True"
#     model = AutoModelForCausalLM.from_pretrained(
#         model_name_or_path,
#         torch_dtype=torch.float16,
#         device_map=0,
#         revision="main",
#     )

#     tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)
#     return model, tokenizer


# system_message = "You are an intelligent programming assistant."
# prompt = "Tell me about AI"
# prompt_template = f"""### System Prompt
# {system_message}

# ### User Message
# {prompt}

# ### Assistant

# """


# def generate_one_completion(model, tokenizer, prompt_template) -> str:
#     input_ids = tokenizer(prompt_template, return_tensors="pt").input_ids.cuda()
#     output = model.generate(inputs=input_ids, temperature=0.1, max_new_tokens=512)
#     result = tokenizer.decode(output[0])
#     return result
