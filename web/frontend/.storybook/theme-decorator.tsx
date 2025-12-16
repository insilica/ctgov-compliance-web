import type { Decorator } from '@storybook/react';
import { AuthProvider } from '../src/providers/AuthProvider';
import '../src/styles/main.scss';

export const withAppTheme: Decorator = (Story, context) => {
  const colorMode = context.globals.backgrounds?.value ?? 'light';

  return (
    <AuthProvider>
      <div data-color-mode={colorMode} style={{ minHeight: '100vh' }}>
        <Story />
      </div>
    </AuthProvider>
  );
};
