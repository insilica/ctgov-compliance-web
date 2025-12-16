import type { Meta, StoryObj } from '@storybook/react';
import { PrimaryButton } from '../components/PrimaryButton';

const meta = {
  title: 'Components/Primary Button',
  component: PrimaryButton,
  args: {
    children: 'Save changes',
  },
  argTypes: {
    onClick: { action: 'clicked' },
  },
} satisfies Meta<typeof PrimaryButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Loading: Story = {
  args: {
    isLoading: true,
  },
};
