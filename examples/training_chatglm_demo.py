# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: 
"""
import sys
import argparse
from loguru import logger
import pandas as pd

sys.path.append('..')
from lmft import ChatGLMTune


def load_data(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip('\n')
            terms = line.split('\t')
            if len(terms) == 3:
                data.append([terms[0], terms[1], terms[2]])
            else:
                logger.warning(f'line error: {line}')
    return data


def finetune_demo():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_file', default='data/train.csv', type=str, help='Training data file')
    parser.add_argument('--test_file', default='data/test.csv', type=str, help='Test data file')
    parser.add_argument('--model_type', default='chatglm', type=str, help='Transformers model type')
    parser.add_argument('--model_name', default='THUDM/chatglm-6b', type=str, help='Transformers model or path')
    parser.add_argument('--do_train', action='store_true', help='Whether to run training.')
    parser.add_argument('--do_predict', action='store_true', help='Whether to run predict.')
    parser.add_argument('--output_dir', default='./outputs/', type=str, help='Model output directory')
    parser.add_argument('--max_seq_length', default=256, type=int, help='Input max sequence length')
    parser.add_argument('--max_length', default=256, type=int, help='Output max sequence length')
    parser.add_argument('--num_epochs', default=3, type=int, help='Number of training epochs')
    parser.add_argument('--batch_size', default=2, type=int, help='Batch size')
    args = parser.parse_args()
    logger.info(args)

    # fine-tune chatGLM model
    if args.do_train:
        logger.info('Loading data...')
        model_args = {
            'use_lora': True,
            "reprocess_input_data": True,
            "overwrite_output_dir": True,
            "max_seq_length": args.max_seq_length,
            "max_length": args.max_length,
            "per_device_train_batch_size": args.batch_size,
            "num_train_epochs": args.num_epochs,
            "save_eval_checkpoints": False,
            "output_dir": args.output_dir,
        }
        model = ChatGLMTune(args.model_type, args.model_name, args=model_args)
        train_data = load_data(args.train_file)
        logger.debug('train_data: {}'.format(train_data[:10]))
        train_df = pd.DataFrame(train_data, columns=["instruction", "input", "output"])

        model.train_model(train_df)
    if args.do_predict:
        model = ChatGLMTune(args.model_type, args.model_name,
                            args={'use_lora': True, 'eval_batch_size': args.batch_size})
        test_data = load_data(args.test_file)[:10]
        test_df = pd.DataFrame(test_data, columns=["instruction", "input", "output"])
        logger.debug('test_df: {}'.format(test_df))

        def get_prompt(arr):
            if arr['input'].strip():
                return f"问：{arr['instruction']}\n{arr['input']}\n答："
            else:
                return f"问：{arr['instruction']}\n答："

        test_df['prompt'] = test_df.apply(get_prompt, axis=1)
        test_df['predict_after'] = model.predict(test_df['prompt'].tolist())

        response, history = model.chat("你好", history=[])
        print(response)
        response, history = model.chat("晚上睡不着应该怎么办", history=history)
        print(response)
        del model

        ref_model = ChatGLMTune(args.model_type, args.model_name,
                                args={'use_lora': False, 'eval_batch_size': args.batch_size})
        test_df['predict_before'] = ref_model.predict(test_df['prompt'].tolist())
        logger.debug('test_df result: {}'.format(test_df))
        out_df = test_df[['instruction', 'input', 'output', 'predict_before', 'predict_after']]
        out_df.to_json('test_result.json', force_ascii=False, orient='records', lines=True)


if __name__ == '__main__':
    finetune_demo()
