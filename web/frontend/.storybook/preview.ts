import type { Preview } from '@storybook/react';
import { withAppTheme } from './theme-decorator';

const preview: Preview = {
  decorators: [withAppTheme],
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    viewport: {
      viewports: {
        tablet: {
          name: 'Tablet',
          styles: { width: '768px', height: '100%' },
        },
        desktop: {
          name: 'Desktop',
          styles: { width: '1280px', height: '100%' },
        },
      },
    },
  },
};

export default preview;
