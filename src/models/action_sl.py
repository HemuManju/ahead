import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from math import floor
from torch.utils.tensorboard import SummaryWriter
from yaml import safe_load
from torchsampler import ImbalancedDatasetSampler
import os

np.random.seed(42)


class ACTION_SL(nn.Module):
    def __init__(self,
                 input_shape=(84, 84),
                 load_model=False,
                 cpt=0,
                 epoch=0,
                 num_actions=18):
        super(ACTION_SL, self).__init__()
        self.input_shape = input_shape
        self.num_actions = num_actions
        with open('src/config.yaml', 'r') as f:
            self.config_yml = safe_load(f.read())
        self.model_save_string = self.config_yml[
            'MODEL_SAVE_DIR'] + "{}".format(
                self.__class__.__name__) + '_Epoch_{}.pt'

        self.writer = SummaryWriter(
            log_dir=os.path.join(self.config_yml['RUNS_DIR'], 'AP0'))
        self.conv1 = nn.Conv2d(4, 32, 8, stride=(4, 4))
        self.pool = nn.MaxPool2d((1, 1), (1, 1), (0, 0), (1, 1))
        # self.pool = lambda x: x

        self.conv2 = nn.Conv2d(32, 64, 4, stride=(2, 2))
        self.conv3 = nn.Conv2d(64, 64, 3, stride=(1, 1))
        self.lin_in_shape = self.lin_in_shape()
        self.linear1 = nn.Linear(64 * np.prod(self.lin_in_shape), 512)
        self.linear2 = nn.Linear(512, 128)
        self.linear3 = nn.Linear(128, self.num_actions)
        self.batch_norm32 = nn.BatchNorm2d(32)
        self.batch_norm64 = nn.BatchNorm2d(64)
        self.dropout = nn.Dropout()

        self.softmax = torch.nn.Softmax()
        self.load_model = load_model
        if self.load_model:
            print(self.model_save_string.format(cpt))
            model_pickle = torch.load(self.model_save_string.format(cpt))
            self.load_state_dict(model_pickle['model_state_dict'])
        self.epoch = epoch

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.batch_norm32(x)
        x = self.dropout(x)

        x = self.pool(F.relu(self.conv2(x)))
        x = self.batch_norm64(x)
        x = self.dropout(x)

        x = self.pool(F.relu(self.conv3(x)))
        x = self.batch_norm64(x)
        x = self.dropout(x)
        x = x.view(-1, 64 * np.prod(self.lin_in_shape))
        x = self.linear1(x)
        x = self.linear2(x)
        x = self.linear3(x)

        return x

    def out_shape(self, layer, in_shape):
        h_in, w_in = in_shape
        h_out, w_out = floor((
            (h_in + 2 * layer.padding[0] - layer.dilation[0] *
             (layer.kernel_size[0] - 1) - 1) / layer.stride[0]) + 1), floor((
                 (w_in + 2 * layer.padding[1] - layer.dilation[1] *
                  (layer.kernel_size[1] - 1) - 1) / layer.stride[1]) + 1)
        return h_out, w_out

    def lin_in_shape(self):
        # TODO create as a wrapper
        # wrapper that gives num params

        # temp written down shape calcer
        out_shape = self.out_shape(self.conv1, self.input_shape)
        out_shape = self.out_shape(self.conv2, out_shape)
        out_shape = self.out_shape(self.conv3, out_shape)
        return out_shape

    def loss_fn(self, loss_, acts, targets):
        # print(targets)
        # print(acts)
        ce_loss = loss_(acts, targets)
        return ce_loss

    def train_loop(self,
                   opt,
                   lr_scheduler,
                   loss_,
                   x_var,
                   y_var,
                   batch_size=32):
        dataset = torch.utils.data.TensorDataset(x_var, y_var)
        train_data = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            sampler=ImbalancedDatasetSampler(dataset),
            shuffle=False)

        self.val_data = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            sampler=ImbalancedDatasetSampler(dataset),
            shuffle=False)

        if self.load_model:
            model_pickle = torch.load(self.model_save_string.format(
                self.epoch))
            self.load_state_dict(model_pickle['model_state_dict'])
            opt.load_state_dict(model_pickle['model_state_dict'])
            self.epoch = model_pickle['epoch']
            loss_val = model_pickle['loss']

        for epoch in range(self.epoch, 20000):
            for i, data in enumerate(train_data):
                x, y = data

                opt.zero_grad()

                acts = self.forward(x)
                loss = self.loss_fn(loss_, acts, y)
                loss.backward()
                opt.step()

                if epoch % 10 == 0:
                    self.writer.add_histogram("acts", y)
                    self.writer.add_histogram("preds", acts)
                    self.writer.add_scalar('Loss', loss.data.item(), epoch)
                    self.writer.add_scalar('Acc', self.accuracy(), epoch)

                    torch.save(
                        {
                            'epoch': epoch,
                            'model_state_dict': self.state_dict(),
                            'optimizer_state_dict': opt.state_dict(),
                            'loss': loss,
                        }, self.model_save_string.format(epoch))

    def infer(self, epoch, x_var):
        if not self.load_model:
            model_pickle = torch.load(self.model_save_string.format(epoch))
            self.load_state_dict(model_pickle['model_state_dict'])
        acts = self.forward(x_var).argmax().data.numpy()
        return acts

    def accuracy(self):
        acc = 0
        ix = 0
        for i, data in enumerate(self.val_data):
            x, y = data
            acts = self.forward(x).argmax(dim=1)
            acc += (acts == y).sum().item()
            ix += y.shape[0]
        return (acc / ix)


if __name__ == "__main__":

    action_net = ACTION_SL()
    rand_image = torch.rand(1, 4, 84, 84)
    rand_target = torch.randint(action_net.num_actions, [1])
    action_net.forward(rand_image)
    optimizer = torch.optim.Adadelta(action_net.parameters(), lr=1.0, rho=0.95)

    # if scheduler is declared, ought to use & update it , else model never trains
    # lr_scheduler = torch.optim.lr_scheduler.LambdaLR(
    #     optimizer, lr_lambda=lambda x: x*0.95)
    lr_scheduler = None

    loss_ = torch.nn.CrossEntropyLoss()
    action_net.train_loop(optimizer,
                          lr_scheduler,
                          loss_,
                          rand_image,
                          rand_target,
                          batch_size=4)
