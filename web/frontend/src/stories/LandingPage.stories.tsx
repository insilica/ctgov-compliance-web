import type { Meta, StoryObj } from '@storybook/react';
import { LandingPage } from '../pages/LandingPage';

const meta = {
  title: 'Pages/Landing Page',
  component: LandingPage,
  parameters: {
    layout: 'fullscreen',
  },
  argTypes: {
    onSignOut: { action: 'signOut' },
  },
} satisfies Meta<typeof LandingPage>;

export default meta;

type Story = StoryObj<typeof meta>;

export const LoggedOut: Story = {
  args: {
    isAuthenticated: false,
  },
};

export const Authenticated: Story = {
  args: {
    isAuthenticated: true,
  },
};
